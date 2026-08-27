from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import pygame

from .chemistry import signature_similarity
from .config import BehaviorModel, Scheduler, SimulationConfig
from .config_io import build_config, load_config_file, save_config_file
from .entities import Organism
from .recording import RunRecorder
from .simulation import Simulation

Color = tuple[int, int, int]
ZOOM_LEVELS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64)
DEFAULT_GUI_SETTINGS = Path("runs/gui_settings.json")


@dataclass(slots=True)
class Slider:
    label: str
    field: str
    minimum: float
    maximum: float
    step: float
    value: float
    live: bool
    rect: pygame.Rect

    def set_from_x(self, x: int) -> None:
        fraction = min(1.0, max(0.0, (x - self.rect.x) / max(1, self.rect.width)))
        raw = self.minimum + fraction * (self.maximum - self.minimum)
        self.value = round(raw / self.step) * self.step
        self.value = min(self.maximum, max(self.minimum, self.value))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, rect: pygame.Rect | None = None) -> None:
        rect = rect or self.rect
        track_y = rect.y + 20
        pygame.draw.line(
            surface,
            (85, 91, 108),
            (rect.left, track_y),
            (rect.right, track_y),
            4,
        )
        fraction = (self.value - self.minimum) / (self.maximum - self.minimum)
        knob_x = round(rect.x + fraction * rect.width)
        pygame.draw.circle(
            surface,
            (92, 196, 255) if self.live else (255, 179, 71),
            (knob_x, track_y),
            7,
        )
        suffix = "live" if self.live else "apply R"
        rendered = font.render(f"{self.label}: {self.value:g} ({suffix})", True, (225, 230, 240))
        surface.blit(rendered, (rect.x, rect.y))


class App:
    def __init__(
        self,
        config: SimulationConfig | None = None,
        *,
        settings_path: Path | None = None,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("Emergent Organism Simulation")
        self.config = config or SimulationConfig()
        self.settings_path = settings_path
        self.world_pixels = 768
        self.screen = pygame.display.set_mode((self.world_pixels + self.config.panel_width, 800), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 17)
        self.simulation = Simulation(self.config)
        self.recorder = RunRecorder(self.simulation, source="gui")
        self.paused = False
        self.show_heat = False
        self.show_food = True
        self.species_colors = True
        self.show_species_view = False
        self.species_scroll = 0
        self.selected_id: int | None = None
        self.inspector_scroll = 0
        self.camera_x = float(self.config.width // 2)
        self.camera_y = float(self.config.height // 2)
        self.follow_selected = True
        self.panning: tuple[int, int, float, float, int] | None = None
        self.sliders_scroll = 0
        self._minimap_bounds: tuple[int, int, int, int, float, int, int] | None = None
        self.accumulator = 0.0
        self.error_message = ""
        self.actual_ticks_per_second = 0.0
        self.dragging: Slider | None = None
        self.sliders = self._make_sliders()

    def _make_sliders(self) -> list[Slider]:
        x = self.world_pixels + 24
        width = self.config.panel_width - 48
        specifications = [
            ("Founders", "founder_count", 50, 600, 10, False),
            ("Genome seeds", "founder_archetype_count", 1, 32, 1, False),
            ("Elements", "element_count", 4, 12, 1, False),
            ("Molecules", "molecule_count", 16, 80, 1, False),
            ("Deposits", "initial_deposits", 500, 5000, 100, False),
            ("Ticks/sec", "ticks_per_second", 1, 120, 1, True),
            ("Heat diffusion", "heat_diffusion", 0, 0.24, 0.01, True),
            ("Primary production", "primary_production_rate", 0, 0.05, 0.0025, True),
            ("Deposit production", "deposit_production_rate", 0, 0.5, 0.01, True),
            ("Prey threshold", "prey_compatibility_threshold", 0.1, 0.9, 0.05, True),
            ("Attack damage", "attack_damage_multiplier", 0.5, 5, 0.25, True),
            ("Decomposition", "decomposition_rate", 0, 0.005, 0.0001, True),
            ("Mutation", "mutation_multiplier", 0, 4, 0.1, True),
            ("Maintenance", "maintenance_cost_multiplier", 0.25, 1.5, 0.05, True),
            ("Maturity age", "maturity_age_multiplier", 0.25, 1.5, 0.05, True),
            ("Repro drive", "reproduction_action_bonus", 0, 3, 0.1, True),
            ("Repro cost", "reproduction_cost_multiplier", 0, 1.5, 0.05, True),
            ("Repro cooldown", "reproduction_cooldown_multiplier", 0.25, 1.5, 0.05, True),
            ("Asexual floor", "asexual_probability_floor", 0, 0.5, 0.01, True),
            ("Sexual floor on", "sexual_probability_floor_enabled", 0, 1, 1, True),
            ("Sexual floor", "sexual_probability_floor", 0, 0.5, 0.01, True),
            ("Random seasons", "seasons_enabled", 0, 1, 1, False),
            ("Season strength", "season_strength", 0, 1, 0.05, False),
            ("Season min", "season_duration_min", 50, 5000, 50, False),
            ("Season max", "season_duration_max", 50, 5000, 50, False),
            ("Season blend", "season_transition_ticks", 0, 1000, 25, False),
            ("Cell affordances", "cellular_emergence_enabled", 0, 1, 1, False),
            ("Move/reproduce as unit", "emergence_coordinated_components", 0, 1, 1, False),
            ("Module limit", "emergence_max_modules", 1, 32, 1, False),
            ("Structural mutation", "emergence_structural_mutation_rate", 0, 0.2, 0.005, False),
            ("Bond chance", "emergence_bond_rate", 0, 0.1, 0.0025, False),
            ("Engulf chance", "emergence_engulfment_rate", 0, 0.1, 0.0025, False),
            ("Biodeposits", "biodeposits_enabled", 0, 1, 1, False),
            ("Bio decay", "biodeposit_decay_rate", 0, 0.01, 0.00025, False),
            ("Bio move resistance", "biodeposit_movement_resistance", 0, 2, 0.05, False),
            ("Bio cover", "biodeposit_cover_strength", 0, 2, 0.05, False),
            ("Bio concealment", "biodeposit_concealment", 0, 1, 0.025, False),
            ("Detail every", "recording_detail_interval", 1, 50, 1, True),
            ("Snapshot every", "recording_snapshot_interval", 1, 50, 1, True),
        ]
        sliders: list[Slider] = []
        for index, (label, field, minimum, maximum, step, live) in enumerate(specifications):
            sliders.append(
                Slider(
                    label,
                    field,
                    float(minimum),
                    float(maximum),
                    float(step),
                    float(getattr(self.config, field)),
                    live,
                    pygame.Rect(x, 258 + index * 25, width, 25),
                )
            )
        return sliders

    def _slider_value(self, slider: Slider) -> float | int | bool:
        value: float | int | bool = slider.value
        current = getattr(self.config, slider.field)
        if isinstance(current, bool):
            return bool(round(value))
        if isinstance(current, int):
            return round(value)
        return value

    def _normalize_slider_dependencies(self, changed_field: str) -> None:
        if changed_field == "element_count" and self.config.molecule_count < self.config.element_count:
            self.config.molecule_count = self.config.element_count
            self._sync_slider("molecule_count")
        elif changed_field == "molecule_count" and self.config.molecule_count < self.config.element_count:
            self.config.element_count = self.config.molecule_count
            self._sync_slider("element_count")
        elif (
            changed_field == "founder_count"
            and self.config.founder_archetype_count > self.config.founder_count
        ):
            self.config.founder_archetype_count = self.config.founder_count
            self._sync_slider("founder_archetype_count")
        elif (
            changed_field == "founder_archetype_count"
            and self.config.founder_archetype_count > self.config.founder_count
        ):
            self.config.founder_count = self.config.founder_archetype_count
            self._sync_slider("founder_count")
        elif (
            changed_field == "season_duration_min"
            and self.config.season_duration_max < self.config.season_duration_min
        ):
            self.config.season_duration_max = self.config.season_duration_min
            self._sync_slider("season_duration_max")
        elif (
            changed_field == "season_duration_max"
            and self.config.season_duration_max < self.config.season_duration_min
        ):
            self.config.season_duration_min = self.config.season_duration_max
            self._sync_slider("season_duration_min")
        if self.config.season_transition_ticks > self.config.season_duration_min:
            self.config.season_transition_ticks = self.config.season_duration_min
            self._sync_slider("season_transition_ticks")

    def _apply_slider_value(self, slider: Slider) -> float | int | bool:
        value = self._slider_value(slider)
        setattr(self.config, slider.field, value)
        self._normalize_slider_dependencies(slider.field)
        return value

    def _save_settings(self) -> None:
        if self.settings_path is None:
            return
        try:
            self.config.validate()
            save_config_file(self.settings_path, self.config)
        except (OSError, TypeError, ValueError) as error:
            self.error_message = f"settings save failed: {error}"

    def reset(self) -> None:
        for slider in self.sliders:
            self._apply_slider_value(slider)
        self.config.molecule_count = max(self.config.element_count, self.config.molecule_count)
        self.config.founder_archetype_count = min(
            self.config.founder_count, self.config.founder_archetype_count
        )
        try:
            next_simulation = Simulation(self.config.evolved())
            next_recorder = RunRecorder(
                next_simulation,
                source="gui_reset",
                previous_run_id=self.recorder.run_id,
            )
            self.recorder.close(self.simulation)
            self.simulation = next_simulation
            self.recorder = next_recorder
            self.error_message = ""
            self.selected_id = None
            self.inspector_scroll = 0
            self.species_scroll = 0
            self.sliders_scroll = 0
            self.panning = None
            self.camera_x = float(self.config.width // 2)
            self.camera_y = float(self.config.height // 2)
            self.follow_selected = True
            self._save_settings()
        except Exception as error:  # noqa: BLE001 - prototype UI surfaces generation failures
            self.error_message = str(error)
            self.paused = True

    def run(self) -> None:
        running = True
        first_frame = True
        measured_ticks = 0
        measurement_started = perf_counter()
        while running:
            elapsed = self.clock.tick(self.config.render_fps) / 1000.0
            events = pygame.event.get()
            redraw = first_frame or bool(events)
            first_frame = False
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (2, 3):
                    if event.pos[0] < self.world_pixels:
                        self.panning = (
                            event.pos[0],
                            event.pos[1],
                            self.camera_x,
                            self.camera_y,
                            self._tile_size(),
                        )
                        self.follow_selected = False
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging = None
                elif event.type == pygame.MOUSEBUTTONUP and event.button in (2, 3):
                    self.panning = None
                elif event.type == pygame.MOUSEMOTION and self.panning:
                    origin_x, origin_y, cam_x, cam_y, tile = self.panning
                    self.camera_x = cam_x - (event.pos[0] - origin_x) / tile
                    self.camera_y = cam_y - (event.pos[1] - origin_y) / tile
                elif event.type == pygame.MOUSEMOTION and self.dragging:
                    self._update_slider(self.dragging, event.pos[0])
                elif event.type == pygame.MOUSEWHEEL:
                    if self.show_species_view:
                        self.species_scroll = max(0, self.species_scroll - event.y)
                    elif self.selected_id is not None:
                        self.inspector_scroll = max(0, min(45, self.inspector_scroll - event.y * 3))
                    else:
                        self._scroll_sliders(-event.y * 3)
            if self._edge_scroll():
                redraw = True
            if not self.paused and not self.error_message and self._tick_due(elapsed):
                self._advance(1)
                measured_ticks += 1
                now = perf_counter()
                measurement_seconds = now - measurement_started
                if measurement_seconds >= 1.0:
                    self.actual_ticks_per_second = measured_ticks / measurement_seconds
                    measured_ticks = 0
                    measurement_started = now
                redraw = True
            if redraw:
                self.draw()
        self.recorder.close(self.simulation)
        pygame.quit()

    def _tick_due(self, elapsed: float) -> bool:
        self.accumulator += elapsed * self.config.ticks_per_second
        if self.accumulator < 1.0:
            return False
        # Never accumulate a multi-tick catch-up batch. When the engine misses
        # its target, replaying that debt blocks pygame events for hundreds of
        # milliseconds and makes the GUI appear frozen.
        self.accumulator = min(self.accumulator - 1.0, 1.0)
        return True

    def _handle_key(self, key: int) -> bool:
        pan = 8
        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_n:
            self._advance(1)
        elif key == pygame.K_r:
            self.reset()
        elif key == pygame.K_h:
            self.show_heat = not self.show_heat
        elif key == pygame.K_f:
            self.show_food = not self.show_food
        elif key == pygame.K_s:
            self.species_colors = not self.species_colors
        elif key == pygame.K_v:
            self.show_species_view = not self.show_species_view
            self.species_scroll = 0
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.camera_x -= pan
            self.follow_selected = False
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.camera_x += pan
            self.follow_selected = False
        elif key in (pygame.K_UP, pygame.K_w):
            self.camera_y -= pan
            self.follow_selected = False
        elif key in (pygame.K_DOWN, pygame.K_x):
            self.camera_y += pan
            self.follow_selected = False
        elif key == pygame.K_COMMA:
            self._change_zoom(-1)
        elif key == pygame.K_PERIOD:
            self._change_zoom(1)
        elif key == pygame.K_c and self.selected_id is not None:
            self.follow_selected = not self.follow_selected
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.config.ticks_per_second = min(240.0, self.config.ticks_per_second + 5)
            self._sync_slider("ticks_per_second")
            self._save_settings()
            self.recorder.record_config(self.simulation.tick, self.config, reason="keyboard_speed")
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.config.ticks_per_second = max(1.0, self.config.ticks_per_second - 5)
            self._sync_slider("ticks_per_second")
            self._save_settings()
            self.recorder.record_config(self.simulation.tick, self.config, reason="keyboard_speed")
        elif key == pygame.K_LEFTBRACKET:
            self.config.seed -= 1
            self._save_settings()
        elif key == pygame.K_RIGHTBRACKET:
            self.config.seed += 1
            self._save_settings()
        return True

    def _advance(self, ticks: int) -> None:
        try:
            for _ in range(ticks):
                self.simulation.step()
                self.recorder.record_tick(self.simulation)
        except Exception as error:  # noqa: BLE001 - pause and expose invariant failures in the UI
            self.error_message = str(error)
            self.paused = True

    def _edge_scroll(self) -> bool:
        """Pan the camera when the mouse rests near a world-viewport edge."""

        if self.follow_selected or self.panning:
            return False
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if not (0 <= mouse_x < self.world_pixels and 0 <= mouse_y < self.world_pixels):
            return False
        margin = 16
        speed = 0.75
        moved = False
        if mouse_x < margin:
            self.camera_x -= speed
            moved = True
        elif mouse_x > self.world_pixels - margin:
            self.camera_x += speed
            moved = True
        if mouse_y < margin:
            self.camera_y -= speed
            moved = True
        elif mouse_y > self.world_pixels - margin:
            self.camera_y += speed
            moved = True
        return moved

    def _slider_viewport(self) -> pygame.Rect:
        return pygame.Rect(self.world_pixels + 12, 258, self.config.panel_width - 24, 472)

    def _max_sliders_scroll(self) -> int:
        return max(0, len(self.sliders) * 25 - self._slider_viewport().height)

    def _scroll_sliders(self, amount: int) -> None:
        self.sliders_scroll = max(0, min(self._max_sliders_scroll(), self.sliders_scroll + amount))

    def _minimap_rect(self) -> pygame.Rect:
        size = 150
        return pygame.Rect(self.world_pixels - size - 10, self.world_pixels - size - 10, size, size)

    def _jump_from_minimap(self, position: tuple[int, int]) -> None:
        bounds = self._minimap_bounds
        if bounds is None:
            return
        x0, y0, _x1, _y1, scale, map_x, map_y = bounds
        self.camera_x = float(x0 + (position[0] - map_x) / scale)
        self.camera_y = float(y0 + (position[1] - map_y) / scale)
        self.follow_selected = False

    def _mouse_down(self, position: tuple[int, int]) -> None:
        if self.show_species_view and position[0] >= self.world_pixels and position[1] >= 272:
            row = self.species_scroll + (position[1] - 272) // 58
            species = self._active_species()
            if 0 <= row < len(species):
                species_id = species[row].species_id
                representative = next(
                    (
                        self.simulation.organisms[organism_id]
                        for organism_id in self.simulation.living_ids
                        if self.simulation.organisms[organism_id].species_id == species_id
                    ),
                    None,
                )
                if representative is not None:
                    self.selected_id = representative.organism_id
                    self.inspector_scroll = 0
                    self.show_species_view = False
            return
        if (
            not self.show_species_view
            and self.selected_id is None
            and self._slider_viewport().collidepoint(position)
        ):
            for slider in self.sliders:
                if slider.rect.move(0, -self.sliders_scroll).collidepoint(position):
                    self.dragging = slider
                    self._update_slider(slider, position[0])
                    return
        if position[0] < self.world_pixels and position[1] < self.world_pixels:
            minimap = self._minimap_rect()
            if self._minimap_bounds is not None and minimap.collidepoint(position):
                self._jump_from_minimap(position)
                self.show_species_view = False
                return
            tile_size = self._tile_size()
            world_x = self.camera_x + (position[0] - self.world_pixels / 2) / tile_size
            world_y = self.camera_y + (position[1] - self.world_pixels / 2) / tile_size
            tile = (int(world_x), int(world_y))
            occupants = self.simulation.world.organism_ids_at(tile)
            self.selected_id = min(occupants) if occupants else None
            self.inspector_scroll = 0
            self.show_species_view = False

    def _update_slider(self, slider: Slider, x: int) -> None:
        slider.set_from_x(x)
        value = self._apply_slider_value(slider)
        self._save_settings()
        if slider.live:
            setattr(self.simulation.config, slider.field, value)
            setattr(self.simulation.world.config, slider.field, value)
            self.recorder.record_config(self.simulation.tick, self.config, reason=f"slider:{slider.field}")

    def _sync_slider(self, field: str) -> None:
        for slider in self.sliders:
            if slider.field == field:
                slider.value = float(getattr(self.config, field))

    def _active_species(self):
        marker_ticks = self.config.new_species_marker_ticks
        return sorted(
            (species for species in self.simulation.species.values() if species.population > 0),
            key=lambda species: (
                -int(
                    species.origin != "founder"
                    and self.simulation.tick - species.created_tick <= marker_ticks
                ),
                -species.created_tick,
                -species.population,
                species.species_id,
            ),
        )

    def _change_zoom(self, direction: int) -> None:
        current = self._tile_size()
        if direction < 0:
            choices = [level for level in ZOOM_LEVELS if level < current]
            self.config.tile_pixels = choices[-1] if choices else ZOOM_LEVELS[0]
        elif direction > 0:
            choices = [level for level in ZOOM_LEVELS if level > current]
            self.config.tile_pixels = choices[0] if choices else ZOOM_LEVELS[-1]

    def _tile_size(self) -> int:
        return max(ZOOM_LEVELS[0], min(ZOOM_LEVELS[-1], self.config.tile_pixels))

    def _visible_tiles(self) -> tuple[int, int, int, int]:
        tile_size = self._tile_size()
        half_width = self.world_pixels / (2 * tile_size)
        half_height = self.world_pixels / (2 * tile_size)
        x0 = int(self.camera_x - half_width) - 1
        y0 = int(self.camera_y - half_height) - 1
        x1 = int(self.camera_x + half_width) + 2
        y1 = int(self.camera_y + half_height) + 2
        return x0, y0, x1, y1

    def draw(self) -> None:
        self.screen.fill((13, 16, 24))
        self._draw_world()
        self._draw_panel()
        pygame.display.flip()

    def _draw_world(self) -> None:
        simulation = self.simulation
        world = simulation.world
        tile_size = self._tile_size()
        selected = simulation.organisms.get(self.selected_id) if self.selected_id else None
        if self.follow_selected and selected and selected.alive:
            self.camera_x = float(selected.position[0])
            self.camera_y = float(selected.position[1])
        pygame.draw.rect(self.screen, (20, 24, 32), (0, 0, self.world_pixels, self.world_pixels))
        x0, y0, x1, y1 = self._visible_tiles()
        half_view = self.world_pixels / 2

        # Generate any unexplored visible chunks so panning the camera reveals
        # the infinite world (the matter this adds is tracked by the audit).
        size = world.chunk_size
        for cx in range(x0 // size, x1 // size + 1):
            for cy in range(y0 // size, y1 // size + 1):
                world.ensure_chunk(cx, cy)

        def screen_xy(x: int, y: int) -> tuple[float, float]:
            return (
                (x - self.camera_x) * tile_size + half_view,
                (y - self.camera_y) * tile_size + half_view,
            )

        if self.show_heat:
            maximum = max(1e-9, world.total_heat() / max(1, sum(1 for c in world.chunks.values() if c.has_heat)))
            for cx in range(x0 // size, x1 // size + 1):
                for cy in range(y0 // size, y1 // size + 1):
                    chunk = world.chunks.get((cx, cy))
                    if chunk is None or not chunk.has_heat:
                        continue
                    intensity = chunk.heat / maximum
                    for ly, lx in np.argwhere(intensity > 0.02):
                        value = float(intensity[ly, lx])
                        color = (int(150 * value), int(45 * value), int(190 * value))
                        sx, sy = screen_xy(cx * size + int(lx), cy * size + int(ly))
                        pygame.draw.rect(self.screen, color, (sx, sy, tile_size, tile_size))

        if self.show_food:
            selected = (
                self.simulation.organisms.get(self.selected_id) if self.selected_id else None
            )
            digestibility = None
            if selected is not None and selected.alive:
                diet = selected.phenotype.diet_signature
                digestibility = {
                    molecule.molecule_id: signature_similarity(molecule.signature, diet)
                    for molecule in simulation.catalog.molecules
                }
            for cx in range(x0 // size, x1 // size + 1):
                for cy in range(y0 // size, y1 // size + 1):
                    chunk = world.chunks.get((cx, cy))
                    if chunk is None:
                        continue
                    for position in chunk.deposit_positions:
                        inventory = world.deposits.get(position)
                        if not inventory:
                            continue
                        richest = max(inventory.values(), key=lambda batch: batch.energy)
                        color = simulation.catalog.molecules[richest.molecule_id].color
                        units = sum(batch.count for batch in inventory.values())
                        square = max(1, min(tile_size, 2 + units // 8))
                        sx, sy = screen_xy(position[0], position[1])
                        rect = pygame.Rect(
                            int(sx + (tile_size - square) / 2),
                            int(sy + (tile_size - square) / 2),
                            square,
                            square,
                        )
                        pygame.draw.rect(self.screen, color, rect)
                        # When inspecting an organism, ring the deposits that
                        # match its diet well enough to be worth eating.
                        if digestibility is not None and digestibility[richest.molecule_id] >= 0.6:
                            pygame.draw.rect(
                                self.screen, (240, 240, 255), rect.inflate(2, 2), 1
                            )

        for corpse in simulation.corpses.values():
            if x0 <= corpse.position[0] < x1 and y0 <= corpse.position[1] < y1:
                sx, sy = screen_xy(corpse.position[0], corpse.position[1])
                pygame.draw.line(self.screen, (100, 92, 86), (sx, sy), (sx + tile_size, sy + tile_size), 1)

        for organism_id in simulation.living_ids:
            organism = simulation.organisms[organism_id]
            ox, oy = organism.position
            if not (x0 - 8 <= ox < x1 + 8 and y0 - 8 <= oy < y1 + 8):
                continue
            species = simulation.species[organism.species_id]
            if self.species_colors:
                color = species.color
            else:
                energy = organism.energy_fraction(simulation.catalog)
                color = (int(255 * (1 - energy)), int(220 * energy), 90)
            if organism.colony_id is not None:
                color = tuple(min(255, channel + 35) for channel in color)
            for x, y in world.footprint(organism):
                if x0 <= x < x1 and y0 <= y < y1:
                    sx, sy = screen_xy(x, y)
                    pygame.draw.rect(self.screen, color, (sx, sy, tile_size, tile_size))
            if organism.mana > 0.5:
                sx, sy = screen_xy(ox, oy)
                pygame.draw.circle(self.screen, (105, 210, 255), (int(sx + tile_size / 2), int(sy + tile_size / 2)), max(1, tile_size // 3))

        if selected is not None and selected.alive:
            for x, y in world.footprint(selected):
                sx, sy = screen_xy(x, y)
                pygame.draw.rect(self.screen, (255, 255, 255), (sx, sy, tile_size, tile_size), 1)

        if selected is not None and selected.alive:
            self._draw_minimap_position(tile_size)
        self._draw_minimap()

    def _draw_minimap_position(self, tile_size: int) -> None:
        """Crosshair marking the camera centre in the infinite world."""

        half_view = self.world_pixels / 2
        cx = half_view
        cy = half_view
        pygame.draw.circle(self.screen, (240, 240, 255), (int(cx), int(cy)), 3, 1)
        label = self.small_font.render(
            f"camera {int(self.camera_x)},{int(self.camera_y)} zoom {tile_size}px", True, (150, 163, 184)
        )
        self.screen.blit(label, (8, self.world_pixels - 20))

    def _draw_minimap(self) -> None:
        """Overview of every explored content with a clickable camera frame."""

        rect = self._minimap_rect()
        simulation = self.simulation
        world = simulation.world
        xs = [position[0] for position in world.deposits]
        ys = [position[1] for position in world.deposits]
        for organism_id in simulation.living_ids:
            x, y = simulation.organisms[organism_id].position
            xs.append(x)
            ys.append(y)
        xs.append(int(self.camera_x))
        ys.append(int(self.camera_y))
        pad = 16
        x0, x1 = min(xs) - pad, max(xs) + pad
        y0, y1 = min(ys) - pad, max(ys) + pad
        scale = min(rect.width / max(1, x1 - x0), rect.height / max(1, y1 - y0))
        self._minimap_bounds = (x0, y0, x1, y1, scale, rect.x, rect.y)
        surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surface.fill((13, 16, 24, 210))
        width, height = rect.width, rect.height
        for position in world.deposits:
            mx = int((position[0] - x0) * scale)
            my = int((position[1] - y0) * scale)
            if 0 <= mx < width and 0 <= my < height:
                surface.set_at((mx, my), (86, 96, 112))
        for organism_id in simulation.living_ids:
            organism = simulation.organisms[organism_id]
            mx = int((organism.position[0] - x0) * scale)
            my = int((organism.position[1] - y0) * scale)
            if 0 <= mx < width and 0 <= my < height:
                surface.set_at((mx, my), simulation.species[organism.species_id].color)
        tile = self._tile_size()
        view_w = self.world_pixels / tile * scale
        view_h = self.world_pixels / tile * scale
        frame = pygame.Rect(
            int((self.camera_x - x0) * scale - view_w / 2),
            int((self.camera_y - y0) * scale - view_h / 2),
            max(4, int(view_w)),
            max(4, int(view_h)),
        )
        frame.clamp_ip(surface.get_rect())
        pygame.draw.rect(surface, (240, 240, 255), frame, 1)
        self.screen.blit(surface, rect.topleft)
        pygame.draw.rect(self.screen, (85, 91, 108), rect, 1)
        self.screen.blit(
            self.small_font.render("minimap", True, (150, 163, 184)),
            (rect.x + 4, rect.y + 2),
        )

    def _draw_panel(self) -> None:
        panel_x = self.world_pixels
        pygame.draw.rect(self.screen, (24, 29, 41), (panel_x, 0, self.screen.get_width() - panel_x, self.screen.get_height()))
        simulation = self.simulation
        living_species = sum(species.population > 0 for species in simulation.species.values())
        lines = [
            "EMERGENT ORGANISMS",
            f"seed {self.config.seed}   tick {simulation.tick}   run {self.recorder.run_id[-8:]}",
            f"population {simulation.population} / born {simulation.stats.births}",
            f"species {living_species}   deaths {simulation.stats.deaths}",
            (
                f"sexual parents {simulation.living_sexual_parent_count}/{len(simulation.sexual_parent_ids)} "
                f"events {simulation.stats.sexual_reproduction_events}"
            ),
            f"magic {simulation.stats.magic_casts}   attacks {simulation.stats.attacks}",
            f"alliances {len(simulation.alliances)}   colonies {len(simulation.colonies)}",
            f"energy error {simulation.last_audit_error:+.2e}",
            f"ticks/s {self.actual_ticks_per_second:.1f} actual / {self.config.ticks_per_second:g} target",
            f"state {'PAUSED' if self.paused else 'RUNNING'}",
        ]
        y = 18
        for index, line in enumerate(lines):
            color: Color = (242, 245, 250) if index == 0 else (190, 201, 218)
            text = self.font.render(line, True, color)
            self.screen.blit(text, (panel_x + 20, y))
            y += 23

        selected = simulation.organisms.get(self.selected_id) if self.selected_id else None
        context_hint: str | None = None
        if self.show_species_view:
            context_hint = "Mouse wheel: scroll  |  click a species: inspect member"
            self._draw_species_view(panel_x)
        elif selected and selected.alive:
            context_hint = "Mouse wheel: scroll genome  |  click empty tile: close"
            self._draw_organism_inspector(panel_x, selected)
        else:
            self.screen.blit(
                self.small_font.render("Click an organism to inspect it and its genome.", True, (205, 211, 225)),
                (panel_x + 20, 242),
            )
            viewport = self._slider_viewport()
            max_scroll = self._max_sliders_scroll()
            self.sliders_scroll = min(self.sliders_scroll, max_scroll)
            previous_clip = self.screen.get_clip()
            self.screen.set_clip(viewport)
            for slider in self.sliders:
                rect = slider.rect.move(0, -self.sliders_scroll)
                if rect.bottom < viewport.top or rect.top > viewport.bottom:
                    continue
                slider.draw(self.screen, self.small_font, rect)
            self.screen.set_clip(previous_clip)
            if max_scroll > 0:
                track_x = panel_x + self.config.panel_width - 16
                pygame.draw.line(self.screen, (60, 66, 82), (track_x, viewport.y), (track_x, viewport.bottom), 3)
                knob_height = max(18, int(viewport.height * viewport.height / (len(self.sliders) * 25)))
                knob_y = viewport.y + (viewport.height - knob_height) * self.sliders_scroll / max_scroll
                pygame.draw.line(
                    self.screen,
                    (150, 158, 176),
                    (track_x, knob_y),
                    (track_x, knob_y + knob_height),
                    3,
                )

        if self.error_message:
            message = self.small_font.render(self.error_message[:52], True, (255, 105, 105))
            self.screen.blit(message, (panel_x + 20, 736))
        elif context_hint:
            self.screen.blit(self.small_font.render(context_hint, True, (150, 163, 184)), (panel_x + 20, 736))
        help_lines = (
            "Space pause  N step  R reset   H heat  F food",
            "S colors  V species   [ ] seed   +/- speed",
            "drag RMB/edges pan, minimap jump  C follow  , . zoom 1–64",
        )
        for index, line in enumerate(help_lines):
            self.screen.blit(self.small_font.render(line, True, (130, 141, 160)), (panel_x + 20, 756 + index * 16))

    def _draw_species_view(self, panel_x: int) -> None:
        species_records = self._active_species()
        heading = self.font.render(f"ACTIVE SPECIES ({len(species_records)})", True, (116, 207, 255))
        self.screen.blit(heading, (panel_x + 20, 242))
        viewport = pygame.Rect(panel_x + 12, 272, self.config.panel_width - 24, 458)
        row_height = 58
        visible_rows = max(1, viewport.height // row_height)
        self.species_scroll = min(self.species_scroll, max(0, len(species_records) - visible_rows))
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(viewport)
        for visible_index, species in enumerate(species_records[self.species_scroll :]):
            y = viewport.y + visible_index * row_height
            if y > viewport.bottom:
                break
            pygame.draw.rect(self.screen, (34, 40, 54), (panel_x + 17, y + 2, self.config.panel_width - 34, row_height - 4))
            pygame.draw.rect(self.screen, species.color, (panel_x + 24, y + 9, 18, 18))
            genome = species.representative_genome
            traits = genome.traits
            is_new = (
                species.origin != "founder"
                and self.simulation.tick - species.created_tick <= self.config.new_species_marker_ticks
            )
            origin_badge = {"founder": "FOUNDER", "mutation": "MUT", "sexual": "SEX"}[species.origin]
            marker = f" NEW {origin_badge}" if is_new else f" {origin_badge}"
            marker_color = (255, 221, 87) if is_new else (232, 236, 244)
            self.screen.blit(
                self.small_font.render(
                    f"Species {species.species_id}{marker}   population {species.population}", True, marker_color
                ),
                (panel_x + 49, y + 7),
            )
            self.screen.blit(
                self.small_font.render(
                    (
                        f"born tick {species.created_tick} parents {species.parent_species_ids or '-'} | "
                        f"births {species.births} deaths {species.deaths}"
                    ),
                    True,
                    (174, 185, 204),
                ),
                (panel_x + 49, y + 23),
            )
            self.screen.blit(
                self.small_font.render(
                    (
                        f"area {traits['adult_area'].center:.1f} basal {traits['basal'].center:.3f} | "
                        f"A {traits['asexual'].center:.2f} S {traits['sexual'].center:.2f} "
                        f"rate x{traits['asexual_rate'].center:.1f}"
                    ),
                    True,
                    (153, 166, 187),
                ),
                (panel_x + 24, y + 39),
            )
        self.screen.set_clip(previous_clip)

    def _draw_organism_inspector(self, panel_x: int, organism: Organism) -> None:
        simulation = self.simulation
        genome = organism.genome
        species = simulation.species[organism.species_id]
        representative_distance = genome.distance(species.representative_genome)
        heading = (116, 207, 255)
        subheading = (255, 187, 92)
        body = (205, 211, 225)
        muted = (150, 163, 184)
        lines: list[tuple[str, Color]] = [
            (f"ORGANISM #{organism.organism_id} / SPECIES {organism.species_id}", heading),
            (f"age {simulation.tick - organism.birth_tick}  generation {organism.generation}", body),
            (f"parents {organism.parent_ids or 'founder'}", body),
            (
                f"area {organism.area(simulation.catalog)}  mass {organism.structural_mass(simulation.catalog)}",
                body,
            ),
            (
                f"energy {organism.energy_fraction(simulation.catalog):.1%}  mana {organism.mana:.3g}",
                body,
            ),
            (f"integrity {organism.integrity:.2f}/{organism.max_integrity:.2f}", body),
            (
                f"toxin {organism.toxin_load:.3g}/{organism.phenotype.toxin_tolerance:.3g}",
                body,
            ),
            (f"last action {organism.last_action}", body),
            (f"offspring {organism.offspring_count}  kills {organism.kills}", body),
            (
                f"sexual parent {'yes' if organism.organism_id in simulation.sexual_parent_ids else 'no'}",
                body,
            ),
            (
                f"asexual chance {organism.phenotype.asexual:.2f}  rate x{organism.phenotype.asexual_rate:.2f}",
                body,
            ),
            (
                (
                    f"maturity {self.simulation._effective_maturity_age(organism)} ticks "
                    f"cooldown until {organism.reproduction_cooldown}"
                ),
                body,
            ),
            ("", body),
            (f"GENOME #{genome.genome_id}", heading),
            (f"parent genomes {genome.parent_genome_ids or 'procedural founder'}", body),
            (f"distance from species representative {representative_distance:.4f}", body),
            ("Trait distributions: center +/- spread", muted),
        ]
        for name, gene in sorted(genome.traits.items()):
            label = name.replace("_", " ")
            lines.append((f"{label:<23} {gene.center:.4g} +/- {gene.spread:.3g}", body))

        vector_fields = (
            ("diet signature", genome.diet_signature),
            ("toxin sensitivity", genome.toxin_sensitivity),
            ("magic affinity F/W/E/A", genome.magic_affinity),
            ("magic resist F/W/E/A", genome.magic_resistance),
        )
        lines.extend((("", body), ("GENOME VECTORS", subheading)))
        for label, genes in vector_fields:
            values = " ".join(f"{gene.center:.2f}" for gene in genes)
            lines.append((f"{label}: {values}", body))

        lines.extend((("", body), ("DOMINANT POLICY DRIVES", subheading)))
        for action, weights in sorted(genome.policy.items()):
            feature, gene = max(weights.items(), key=lambda item: item[1].center)
            lines.append((f"{action:<10} -> {feature} ({gene.center:+.2f})", body))

        viewport = pygame.Rect(panel_x + 12, 258, self.config.panel_width - 24, 472)
        visible_lines = max(1, viewport.height // 17)
        self.inspector_scroll = min(self.inspector_scroll, max(0, len(lines) - visible_lines))
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(viewport)
        y = viewport.y - self.inspector_scroll * 17
        for text, color in lines:
            if y + 17 >= viewport.top and y <= viewport.bottom:
                self.screen.blit(self.small_font.render(text, True, color), (panel_x + 20, y))
            y += 17
        self.screen.set_clip(previous_clip)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the pygame organism simulation")
    parser.add_argument(
        "--engine",
        choices=("auto", "rust", "python"),
        default="auto",
        help="GUI kernel (auto prefers the asynchronous Rust engine)",
    )
    parser.add_argument("--config", type=Path, help="load JSON or TOML simulation settings")
    parser.add_argument(
        "--behavior-model",
        choices=tuple(model.value for model in BehaviorModel),
        help="startup-selected behavior/controller law",
    )
    parser.add_argument(
        "--scheduler",
        choices=tuple(scheduler.value for scheduler in Scheduler),
        help="versioned Rust scheduler (parallel-v3 requires a V2 behavior model)",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        help="parallel-v3 Rayon workers; zero uses the machine-local default",
    )
    parser.add_argument(
        "--settings-out",
        type=Path,
        default=DEFAULT_GUI_SETTINGS,
        help="JSON file updated when GUI settings change",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="ignore the automatically saved GUI settings when --config is omitted",
    )
    parser.add_argument(
        "--no-save-settings",
        action="store_true",
        help="do not write GUI settings",
    )
    args = parser.parse_args()

    source = args.config
    if source is None and not args.fresh and args.settings_out.exists():
        source = args.settings_out
    try:
        simulation_values, _ = load_config_file(source) if source else ({}, {})
        overrides = {}
        if args.behavior_model is not None:
            overrides["behavior_model"] = BehaviorModel(args.behavior_model)
        if args.scheduler is not None:
            overrides["scheduler"] = Scheduler(args.scheduler)
        if args.parallel_workers is not None:
            overrides["parallel_workers"] = args.parallel_workers
        config = build_config(simulation_values, overrides)
        settings_path = None if args.no_save_settings else args.settings_out
        if settings_path is not None:
            save_config_file(settings_path, config)
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))

    if args.engine != "python":
        from .rust_kernel import extension_available

        if extension_available():
            from .native_app import NativeApp

            NativeApp(config, settings_path=settings_path).run()
            return
        if args.engine == "rust":
            parser.error("Rust kernel is unavailable; run `nu rust/install_release.nu`")
    App(config, settings_path=settings_path).run()


if __name__ == "__main__":
    main()
