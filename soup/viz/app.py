"""Interactive pygame viewer for the Stage 0 flat BFF soup.

The square arrangement is a display layout only. Tape programs cannot observe it,
and pairing remains globally random exactly as in headless Stage 0 runs.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pygame
from numpy.typing import NDArray

from soup.config import Config
from soup.interactions import InteractionFact
from soup.simulation import Simulation
from soup.substrate.bff import INSTRUCTION_SET, INSTRUCTIONS


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


class Stage0Viewer:
    """Render and interactively advance one deterministic simulation prefix."""

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
        self.panel_width = 430
        self.width = max(980, self.grid_left + self.grid_width + self.panel_width + 36)
        self.height = max(720, self.grid_top + self.grid_height + 80)
        self.state = ViewerState(
            speed=self.config.viz.ticks_per_frame,
            colour_mode=self.config.viz.colour_mode,
            activity=np.zeros(population, dtype=np.float64),
        )
        self._step_once = False
        self._frames = 0

    def run(self, max_frames: int | None = None) -> Path:
        """Open the viewer, preserving normal raw logs for every executed tick."""

        pygame.init()
        pygame.display.set_caption("Program Soup — Stage 0 BFF")
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
                    self.state.speed = min(1024, self.state.speed * 2)
                elif event.key in (pygame.K_DOWN, pygame.K_MINUS):
                    self.state.speed = max(1, self.state.speed // 2)
                elif event.key == pygame.K_c:
                    modes = ("content_hash", "dominant_opcode", "activity")
                    self.state.colour_mode = modes[(modes.index(self.state.colour_mode) + 1) % len(modes)]
                elif event.key == pygame.K_s:
                    self._save_screenshot()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                column = (mouse_x - self.grid_left) // self.cell_px
                row = (mouse_y - self.grid_top) // self.cell_px
                if 0 <= column < self.columns and 0 <= row < self.rows:
                    index = row * self.columns + column
                    if index < self.simulation.world.population_size:
                        self.state.selected = index
        return True

    def _record_tick(self, facts: list[InteractionFact]) -> None:
        changed: set[int] = set()
        writes = 0
        for fact in facts:
            writes += fact.writes_success
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
        screen.blit(title.render("BFF primordial soup", True, TEXT), (self.grid_left, 18))
        subtitle = "display grid only — interactions are globally random"
        screen.blit(small.render(subtitle, True, MUTED), (self.grid_left + 250, 25))
        self._draw_grid(screen)
        panel_x = self.grid_left + self.grid_width + 28
        pygame.draw.rect(screen, PANEL, (panel_x, 16, self.panel_width, self.height - 32), border_radius=8)
        self._draw_panel(screen, panel_x + 18, font, small, title)
        controls = "SPACE pause  →/N step  ↑/↓ speed  C colour  click inspect  S screenshot  Q quit"
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
        lines = (
            f"tick       {self.state.tick:,} / {self.config.run.n_ticks:,}",
            f"speed      {self.state.speed} tick(s)/frame",
            f"tapes      {self.simulation.world.population_size}",
            f"distinct   {distinct}",
            f"changed    {changed} last tick",
            f"writes     {writes} last tick",
            f"colour     {self.state.colour_mode}",
        )
        for line in lines:
            screen.blit(font.render(line, True, TEXT), (x, y))
            y += 21
        y += 7
        screen.blit(font.render("Distinct hashes", True, TEXT), (x, y))
        y += 20
        self._draw_chart(screen, x, y, 390, 82, self.state.distinct_history, ACCENT)
        y += 99
        screen.blit(font.render("Changed tapes / tick", True, TEXT), (x, y))
        y += 20
        self._draw_chart(screen, x, y, 390, 65, self.state.changed_history, ACTIVE)
        y += 82
        self._draw_inspector(screen, x, y, small, font)

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
    return Stage0Viewer(simulation).run(max_frames=max_frames)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Stage 0 TOML configuration")
    parser.add_argument("--max-frames", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    print(run_visual(args.config, max_frames=args.max_frames))


if __name__ == "__main__":
    main()
