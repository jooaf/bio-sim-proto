"""Interactive pygame experiment UI for the flat Stage 0/1 BFF soup.

The square arrangement is a display layout only. Runtime-safe experiment parameters
can be changed at tick boundaries; every accepted change is persisted in run logs.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import numpy as np
import pygame
from numpy.typing import NDArray

from soup.config import Config, PairingMode
from soup.interactions import InteractionFact
from soup.simulation import Simulation
from soup.substrate.base import ExecutionBudget
from soup.substrate.bff import BFFSubstrate, INSTRUCTION_SET, INSTRUCTIONS


Color = tuple[int, int, int]
BACKGROUND: Color = (14, 17, 23)
PANEL: Color = (25, 30, 40)
TEXT: Color = (225, 230, 238)
MUTED: Color = (137, 148, 166)
ACCENT: Color = (86, 205, 255)
ACTIVE: Color = (255, 211, 77)
GRID_LINE: Color = (38, 45, 58)
OPCODE_COLORS: tuple[Color, ...] = (
    (92, 158, 255),
    (65, 205, 150),
    (180, 120, 255),
    (255, 132, 105),
    (255, 210, 80),
    (245, 105, 180),
    (85, 220, 225),
    (255, 165, 75),
    (125, 220, 105),
    (225, 110, 125),
)


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    path: str
    step: float = 1.0
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[object, ...] = ()


PARAMETER_SPECS = {
    spec.path: spec
    for spec in (
        ParameterSpec("run.n_ticks", step=1_000, minimum=1),
        ParameterSpec("run.debug_invariants", choices=(False, True)),
        ParameterSpec("run.invariant_check_interval", minimum=1),
        ParameterSpec("substrate.max_steps", step=128, minimum=1),
        ParameterSpec("substrate.head_wrap", choices=(False, True)),
        ParameterSpec("substrate.pc_wrap", choices=(False, True)),
        ParameterSpec("world.interactions_per_tick", minimum=1),
        ParameterSpec("world.pairing_mode", choices=tuple(mode.value for mode in PairingMode)),
        ParameterSpec("world.mutation_rate", step=1.0 / 4096.0, minimum=0.0, maximum=1.0),
        ParameterSpec("logging.tape_snapshot_interval", minimum=1),
        ParameterSpec("logging.full_tape_snapshot_interval", step=100, minimum=0),
        ParameterSpec("logging.interaction_log_rate", step=0.05, minimum=0.0, maximum=1.0),
        ParameterSpec("logging.flush_interval", step=10, minimum=1),
        ParameterSpec("logging.abundance_event_threshold", minimum=2),
        ParameterSpec("viz.fps_cap", step=5, minimum=1, maximum=240),
        ParameterSpec("viz.render_every", minimum=1),
        ParameterSpec("viz.ticks_per_frame", minimum=1, maximum=1024),
        ParameterSpec("viz.colour_mode", choices=("content_hash", "dominant_opcode", "activity")),
    )
}


@dataclass(slots=True)
class ViewerState:
    tick: int = 0
    paused: bool = False
    selected: int | None = None
    speed: int = 1
    colour_mode: str = "content_hash"
    activity: NDArray[np.float64] = field(default_factory=lambda: np.zeros(0, dtype=np.float64))
    distinct_history: deque[int] = field(default_factory=lambda: deque(maxlen=300))
    changed_history: deque[int] = field(default_factory=lambda: deque(maxlen=300))
    write_history: deque[int] = field(default_factory=lambda: deque(maxlen=300))
    recent: deque[InteractionFact] = field(default_factory=lambda: deque(maxlen=10))
    selected_parameter: int = 0
    parameter_message: str = ""


def hash_color(content_hash: str) -> Color:
    """Map a stable tape hash to a bright, stable RGB colour."""

    raw = bytes.fromhex(content_hash[:6])
    return tuple(65 + value * 175 // 255 for value in raw)  # type: ignore[return-value]


def blend(first: Color, second: Color, amount: float) -> Color:
    amount = min(1.0, max(0.0, amount))
    return tuple(int(a * (1.0 - amount) + b * amount) for a, b in zip(first, second, strict=True))  # type: ignore[return-value]


def dominant_opcode_color(tape: NDArray[np.uint8]) -> Color:
    counts = Counter(int(value) for value in tape if int(value) in INSTRUCTION_SET)
    if not counts:
        return (48, 53, 64)
    dominant = min(counts, key=lambda opcode: (-counts[opcode], INSTRUCTIONS.index(opcode)))
    return OPCODE_COLORS[INSTRUCTIONS.index(dominant)]


class SoupViewer:
    """Render and interactively control one fully logged simulation prefix."""

    def __init__(self, simulation: Simulation) -> None:
        self.simulation = simulation
        self.config = simulation.config
        population = simulation.world.population_size
        self.columns = math.ceil(math.sqrt(population))
        self.rows = math.ceil(population / self.columns)
        self.cell_px = self.config.viz.cell_px
        self.grid_left = 24
        self.grid_top = 54
        self.grid_width = self.columns * self.cell_px
        self.grid_height = self.rows * self.cell_px
        self.panel_width = 500
        self.width = max(980, self.grid_left + self.grid_width + self.panel_width + 36)
        self.height = max(720, self.grid_top + self.grid_height + 80)
        self.state = ViewerState(
            speed=self.config.viz.ticks_per_frame,
            colour_mode=self.config.viz.colour_mode,
            activity=np.zeros(population, dtype=np.float64),
        )
        self.live_parameters = [
            PARAMETER_SPECS[path] for path in self.config.viz.live_tunable if path in PARAMETER_SPECS
        ]
        self._parameter_rows: list[tuple[pygame.Rect, int]] = []
        self._step_once = False
        self._frames = 0

    def run(self, max_frames: int | None = None) -> Path:
        """Open the viewer, preserving normal raw logs for every executed tick."""

        pygame.init()
        pygame.display.set_caption(f"Program Soup — Stage {self.config.run.stage} BFF")
        screen = pygame.display.set_mode((self.width, self.height))
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("Menlo", 15)
        small = pygame.font.SysFont("Menlo", 12)
        title = pygame.font.SysFont("Menlo", 19, bold=True)
        running = True
        exit_status = "stopped_by_user"
        try:
            while running and self.state.tick < self.config.run.n_ticks:
                running = self._handle_events()
                should_advance = not self.state.paused or self._step_once
                if should_advance:
                    ticks = 1 if self._step_once else self.state.speed
                    self._step_once = False
                    for _ in range(ticks):
                        if self.state.tick >= self.config.run.n_ticks:
                            break
                        facts = self.simulation.scheduler.advance(self.state.tick)
                        self._record_tick(facts)
                        self.state.tick += 1
                self.state.activity *= 0.84
                if self.state.tick % self.config.viz.render_every == 0 or self.state.paused:
                    self._draw(screen, font, small, title)
                    pygame.display.flip()
                clock.tick(self.config.viz.fps_cap)
                self._frames += 1
                if max_frames is not None and self._frames >= max_frames:
                    running = False
            if self.state.tick >= self.config.run.n_ticks:
                exit_status = "success"
            self.simulation.writer.append_event(
                tick=self.state.tick,
                event_type="visualization_closed",
                details={"completed": exit_status == "success", "frames": self._frames},
            )
        except BaseException:
            self.simulation.writer.close(exit_status="failed")
            raise
        else:
            self.simulation.writer.close(exit_status=exit_status)
        finally:
            pygame.quit()
        return self.simulation.writer.run_dir

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
                if event.key == pygame.K_SPACE:
                    self.state.paused = not self.state.paused
                elif event.key in (pygame.K_RIGHT, pygame.K_n):
                    self.state.paused = True
                    self._step_once = True
                elif event.key in (pygame.K_UP, pygame.K_EQUALS):
                    self._set_parameter_value("viz.ticks_per_frame", min(1024, self.state.speed * 2))
                elif event.key in (pygame.K_DOWN, pygame.K_MINUS):
                    self._set_parameter_value("viz.ticks_per_frame", max(1, self.state.speed // 2))
                elif event.key == pygame.K_c:
                    modes = ("content_hash", "dominant_opcode", "activity")
                    next_mode = modes[(modes.index(self.state.colour_mode) + 1) % len(modes)]
                    self._set_parameter_value("viz.colour_mode", next_mode)
                elif event.key == pygame.K_TAB and self.live_parameters:
                    direction = -1 if event.mod & pygame.KMOD_SHIFT else 1
                    self.state.selected_parameter = (self.state.selected_parameter + direction) % len(self.live_parameters)
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    direction = -1 if event.key == pygame.K_LEFTBRACKET else 1
                    multiplier = 10 if event.mod & pygame.KMOD_SHIFT else 1
                    self._adjust_selected_parameter(direction, multiplier)
                elif event.key == pygame.K_s:
                    self._save_screenshot()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                parameter_hit = False
                for rect, parameter_index in self._parameter_rows:
                    if rect.collidepoint(event.pos):
                        self.state.selected_parameter = parameter_index
                        direction = -1 if mouse_x < rect.centerx else 1
                        self._adjust_selected_parameter(direction, 1)
                        parameter_hit = True
                        break
                if parameter_hit:
                    continue
                column = (mouse_x - self.grid_left) // self.cell_px
                row = (mouse_y - self.grid_top) // self.cell_px
                if 0 <= column < self.columns and 0 <= row < self.rows:
                    index = row * self.columns + column
                    if index < self.simulation.world.population_size:
                        self.state.selected = index
        return True

    def _get_parameter_value(self, path: str) -> object:
        section_name, field_name = path.split(".", 1)
        return getattr(getattr(self.config, section_name), field_name)

    def _assign_parameter_value(self, path: str, value: object) -> None:
        section_name, field_name = path.split(".", 1)
        setattr(getattr(self.config, section_name), field_name, value)

    def _adjust_selected_parameter(self, direction: int, multiplier: int) -> None:
        if not self.live_parameters:
            return
        spec = self.live_parameters[self.state.selected_parameter % len(self.live_parameters)]
        old_value = self._get_parameter_value(spec.path)
        if spec.choices:
            choice_index = spec.choices.index(old_value)
            new_value = spec.choices[(choice_index + direction) % len(spec.choices)]
        elif isinstance(old_value, (int, float)) and not isinstance(old_value, bool):
            candidate = float(old_value) + direction * multiplier * spec.step
            if spec.minimum is not None:
                candidate = max(spec.minimum, candidate)
            if spec.maximum is not None:
                candidate = min(spec.maximum, candidate)
            new_value = int(candidate) if isinstance(old_value, int) else round(candidate, 12)
        else:
            self.state.parameter_message = f"{spec.path} is not adjustable"
            return
        self._set_parameter_value(spec.path, new_value)

    def _set_parameter_value(self, path: str, new_value: object) -> None:
        old_value = self._get_parameter_value(path)
        if old_value == new_value:
            return
        self._assign_parameter_value(path, new_value)
        try:
            self.config.validate()
        except ValueError as error:
            self._assign_parameter_value(path, old_value)
            self.state.parameter_message = f"Rejected: {error}"
            return

        if path == "substrate.max_steps":
            self.simulation.scheduler.budget = ExecutionBudget(max_steps=cast(int, new_value))
        elif path == "substrate.head_wrap" and isinstance(self.simulation.substrate, BFFSubstrate):
            self.simulation.substrate.head_wrap = bool(new_value)
        elif path == "substrate.pc_wrap" and isinstance(self.simulation.substrate, BFFSubstrate):
            self.simulation.substrate.pc_wrap = bool(new_value)
        elif path == "viz.ticks_per_frame":
            self.state.speed = cast(int, new_value)
        elif path == "viz.colour_mode":
            self.state.colour_mode = str(new_value)

        self.simulation.writer.record_parameter_change(
            tick=self.state.tick,
            path=path,
            old_value=old_value,
            new_value=new_value,
        )
        self.state.parameter_message = f"Updated {path}: {old_value} → {new_value}"

    def _record_tick(self, facts: list[InteractionFact]) -> None:
        changed: set[int] = set()
        writes = 0
        for fact in facts:
            writes += fact.writes_success + fact.mutation_writes_success
            if fact.a_bytes_changed:
                changed.add(fact.a_index)
            if fact.b_bytes_changed:
                changed.add(fact.b_index)
            if fact.a_bytes_changed or fact.b_bytes_changed:
                self.state.recent.append(fact)
        if changed:
            self.state.activity[list(changed)] = 1.0
        hashes = {self.simulation.writer.hash_tape(tape) for tape in self.simulation.world.tapes}
        self.state.distinct_history.append(len(hashes))
        self.state.changed_history.append(len(changed))
        self.state.write_history.append(writes)

    def _tape_color(self, index: int) -> Color:
        tape = self.simulation.world.tapes[index]
        if self.state.colour_mode == "dominant_opcode":
            base = dominant_opcode_color(tape)
        elif self.state.colour_mode == "activity":
            intensity = float(self.state.activity[index])
            return blend((35, 39, 49), ACTIVE, intensity)
        else:
            base = hash_color(self.simulation.writer.hash_tape(tape))
        return blend(base, ACTIVE, float(self.state.activity[index]) * 0.65)

    def _draw(
        self,
        screen: pygame.Surface,
        font: pygame.font.Font,
        small: pygame.font.Font,
        title: pygame.font.Font,
    ) -> None:
        screen.fill(BACKGROUND)
        screen.blit(title.render(f"BFF soup — Stage {self.config.run.stage}", True, TEXT), (self.grid_left, 18))
        subtitle = f"display grid only — {self.config.world.pairing_mode.replace('_', ' ')} pairs"
        screen.blit(small.render(subtitle, True, MUTED), (self.grid_left + 250, 25))
        self._draw_grid(screen)
        panel_x = self.grid_left + self.grid_width + 28
        pygame.draw.rect(screen, PANEL, (panel_x, 16, self.panel_width, self.height - 32), border_radius=8)
        self._draw_panel(screen, panel_x + 18, font, small, title)
        controls = "SPACE pause  →/N step  TAB parameter  [ / ] adjust  ↑/↓ speed  C colour  S shot  Q quit"
        screen.blit(small.render(controls, True, MUTED), (self.grid_left, self.height - 28))

    def _draw_grid(self, screen: pygame.Surface) -> None:
        for index in range(self.simulation.world.population_size):
            column = index % self.columns
            row = index // self.columns
            rect = pygame.Rect(
                self.grid_left + column * self.cell_px,
                self.grid_top + row * self.cell_px,
                self.cell_px,
                self.cell_px,
            )
            pygame.draw.rect(screen, self._tape_color(index), rect.inflate(-2, -2), border_radius=2)
            if index == self.state.selected:
                pygame.draw.rect(screen, TEXT, rect, width=2, border_radius=2)
            else:
                pygame.draw.rect(screen, GRID_LINE, rect, width=1)

    def _draw_panel(
        self,
        screen: pygame.Surface,
        x: int,
        font: pygame.font.Font,
        small: pygame.font.Font,
        title: pygame.font.Font,
    ) -> None:
        y = 31
        status = "PAUSED" if self.state.paused else "RUNNING"
        screen.blit(title.render(status, True, ACTIVE if self.state.paused else ACCENT), (x, y))
        y += 32
        distinct = self.state.distinct_history[-1] if self.state.distinct_history else self.simulation.world.population_size
        changed = self.state.changed_history[-1] if self.state.changed_history else 0
        writes = self.state.write_history[-1] if self.state.write_history else 0
        pool_total = 0 if self.simulation.pool is None else self.simulation.pool.total
        lines = (
            f"tick       {self.state.tick:,} / {self.config.run.n_ticks:,}",
            f"speed      {self.state.speed} tick(s)/frame",
            f"tapes      {self.simulation.world.population_size}",
            f"pool       {pool_total:,} free bytes",
            f"distinct   {distinct}",
            f"changed    {changed} last tick",
            f"writes     {writes} last tick",
        )
        for line in lines:
            screen.blit(font.render(line, True, TEXT), (x, y))
            y += 21
        y += 5
        y = self._draw_live_parameters(screen, x, y, small, font)
        y += 7
        screen.blit(font.render("Distinct hashes", True, TEXT), (x, y))
        y += 20
        self._draw_chart(screen, x, y, 460, 58, self.state.distinct_history, ACCENT)
        y += 72
        self._draw_inspector(screen, x, y, small, font)

    def _draw_live_parameters(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        small: pygame.font.Font,
        font: pygame.font.Font,
    ) -> int:
        self._parameter_rows.clear()
        screen.blit(font.render("Live experiment parameters", True, TEXT), (x, y))
        y += 21
        if not self.live_parameters:
            screen.blit(small.render("No viz.live_tunable paths configured", True, MUTED), (x, y))
            return y + 18
        selected = self.state.selected_parameter % len(self.live_parameters)
        start = max(0, min(selected - 2, len(self.live_parameters) - 6))
        for parameter_index in range(start, min(len(self.live_parameters), start + 6)):
            spec = self.live_parameters[parameter_index]
            value = self._get_parameter_value(spec.path)
            rect = pygame.Rect(x, y, 460, 19)
            if parameter_index == selected:
                pygame.draw.rect(screen, (42, 58, 72), rect, border_radius=3)
            value_text = f"{value:.6g}" if isinstance(value, float) else str(value)
            label = f"−  {spec.path:<36} {value_text:>12}  +"
            color = ACCENT if parameter_index == selected else MUTED
            screen.blit(small.render(label, True, color), (x + 4, y + 2))
            self._parameter_rows.append((rect, parameter_index))
            y += 20
        if self.state.parameter_message:
            screen.blit(small.render(self.state.parameter_message[:68], True, ACTIVE), (x, y + 1))
            y += 18
        return y

    @staticmethod
    def _draw_chart(
        screen: pygame.Surface,
        x: int,
        y: int,
        width: int,
        height: int,
        values: deque[int],
        color: Color,
    ) -> None:
        pygame.draw.rect(screen, BACKGROUND, (x, y, width, height), border_radius=4)
        if len(values) < 2:
            return
        points_values = list(values)
        low = min(points_values)
        high = max(points_values)
        spread = max(1, high - low)
        points: list[tuple[int, int]] = []
        for index, value in enumerate(points_values):
            px = x + index * (width - 1) // (len(points_values) - 1)
            py = y + height - 3 - (value - low) * (height - 7) // spread
            points.append((px, py))
        pygame.draw.lines(screen, color, False, points, width=2)

    def _draw_inspector(
        self,
        screen: pygame.Surface,
        x: int,
        y: int,
        small: pygame.font.Font,
        font: pygame.font.Font,
    ) -> None:
        if self.state.selected is None:
            screen.blit(font.render("Click a tape to inspect it", True, MUTED), (x, y))
            return
        index = self.state.selected
        tape = self.simulation.world.tapes[index]
        content_hash = self.simulation.writer.hash_tape(tape)
        screen.blit(font.render(f"Tape {index}", True, TEXT), (x, y))
        y += 21
        facts = (
            f"hash {content_hash[:20]}…",
            f"age {int(self.simulation.world.ages[index])}  nonzero {int(np.count_nonzero(tape))}/{len(tape)}",
            f"instructions {sum(int(value) in INSTRUCTION_SET for value in tape)}",
        )
        for line in facts:
            screen.blit(small.render(line, True, MUTED), (x, y))
            y += 17
        y += 3
        for offset in range(0, len(tape), 32):
            chunk = tape[offset : offset + 32]
            chars = "".join(chr(int(value)) if int(value) in INSTRUCTION_SET else "·" for value in chunk)
            hexes = " ".join(f"{int(value):02x}" for value in chunk[:16])
            screen.blit(small.render(f"{offset:02d} {chars}", True, ACTIVE), (x, y))
            y += 16
            screen.blit(small.render(f"   {hexes}", True, MUTED), (x, y))
            y += 16
            if y > self.height - 45:
                break

    def _save_screenshot(self) -> None:
        surface = pygame.display.get_surface()
        if surface is None:
            return
        target = self.simulation.writer.run_dir / f"screenshot_tick_{self.state.tick}.png"
        pygame.image.save(surface, target)
        self.simulation.writer.append_event(
            tick=self.state.tick,
            event_type="screenshot_saved",
            details={"path": target.name},
        )


def run_visual(config_path: Path, max_frames: int | None = None) -> Path:
    config = Config.load(config_path)
    config.viz.enabled = True
    simulation = Simulation(config)
    return SoupViewer(simulation).run(max_frames=max_frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Stage 0 or Stage 1 TOML configuration")
    parser.add_argument("--max-frames", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    print(run_visual(args.config, max_frames=args.max_frames))


if __name__ == "__main__":
    main()
