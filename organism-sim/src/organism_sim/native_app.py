from __future__ import annotations

from pathlib import Path
from time import time_ns
from typing import Any

import numpy as np
import pygame

from .app import App, Color, Slider
from .config import Scheduler, SimulationConfig
from .gui_backend import RustGuiWorker
from .native_recording import NativeGuiRecorder
from .world import World

DENSE_RENDER_THRESHOLD = 10_000


class NativeApp(App):
    """Pygame view over an asynchronously running Rust kernel."""

    def __init__(
        self,
        config: SimulationConfig | None = None,
        *,
        record: bool = True,
        settings_path: Path | None = None,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("Emergent Organism Simulation — native")
        self.config = config or SimulationConfig()
        self._normalize_cellular_scheduler()
        self.settings_path = settings_path
        self.world_pixels = 768
        self.screen = pygame.display.set_mode(
            (self.world_pixels + self.config.panel_width, 800), pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 17)
        self.paused = False
        self.turbo = True
        self.show_heat = False
        self.show_food = True
        self.species_colors = True
        self.show_cellular = True
        self.cellular_peak_group_size = 0
        self.cellular_peak_groups = 0
        self.cellular_peak_bonds = 0
        self.show_species_view = False
        self.species_scroll = 0
        self.selected_id: int | None = None
        self.inspector_scroll = 0
        self._relation_hitboxes: list[tuple[pygame.Rect, int]] = []
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
        self.snapshot: dict[str, Any] | None = None
        self._snapshot_sequence = 0
        self._viewport_key: tuple[object, ...] | None = None
        self._record = record
        self.recorder = NativeGuiRecorder(self.config) if record else None
        self.run_id = self.recorder.run_id if self.recorder else f"native-{time_ns():x}"
        self.worker = self._new_worker()

    def _normalize_cellular_scheduler(self) -> None:
        """Use the serial scheduler when coordinated groups are enabled.

        The parallel scheduler deliberately rejects coordinated cellular
        components because their rigid movement and shared action authority are
        not yet part of its conflict resolver. Make the GUI slider path
        usable instead of leaving the user with an opaque reset-time error.
        """

        if (
            self.config.cellular_emergence_enabled
            and self.config.emergence_coordinated_components
            and self.config.scheduler == Scheduler.PARALLEL_V3
        ):
            self.config.scheduler = Scheduler.SERIAL_V2

    def _new_worker(self) -> RustGuiWorker:
        return RustGuiWorker(
            self.config.evolved(audit_every=0),
            snapshot_hz=min(10.0, float(self.config.render_fps)),
            target_ticks_per_second=None
            if self.turbo
            else self.config.ticks_per_second,
            start_paused=self.paused,
        )

    def _make_sliders(self) -> list[Slider]:
        sliders = super()._make_sliders()
        for slider in sliders:
            if slider.field == "founder_count":
                slider.maximum = 5000.0
            elif slider.field == "ticks_per_second":
                slider.maximum = 2000.0
        return [
            slider
            for slider in sliders
            if slider.field
            not in {
                "recording_detail_interval",
                "recording_snapshot_interval",
            }
        ]

    @property
    def _tick(self) -> int:
        return int(self.snapshot["tick"]) if self.snapshot else self.worker.status.tick

    def _observe_cellular_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Retain sampled peak group facts so brief bonds are still visible in the UI."""

        stats = snapshot.get("stats", {})
        if not bool(stats.get("cellular_affordances_enabled", False)):
            return
        self.cellular_peak_group_size = max(
            self.cellular_peak_group_size,
            int(stats.get("largest_bond_component", 0)),
        )
        self.cellular_peak_groups = max(
            self.cellular_peak_groups,
            int(stats.get("bond_components", 0)),
        )
        self.cellular_peak_bonds = max(
            self.cellular_peak_bonds,
            int(stats.get("physical_bonds", 0)),
        )

    def _record_applied_config_updates(self) -> None:
        updates = self.worker.drain_applied_config_updates()
        if self.recorder is None:
            return
        for update in updates:
            self.recorder.record_config_update(update.tick, update.changes)

    def reset(self) -> None:
        for slider in self.sliders:
            self._apply_slider_value(slider)
        self.config.molecule_count = max(
            self.config.element_count, self.config.molecule_count
        )
        self.config.founder_archetype_count = min(
            self.config.founder_count, self.config.founder_archetype_count
        )
        self._normalize_cellular_scheduler()
        try:
            previous_run_id = self.run_id
            self.worker.stop()
            self._record_applied_config_updates()
            if self.recorder is not None:
                self.recorder.close(self.worker.status)
            self.worker = self._new_worker()
            self.worker.start()
            self.snapshot = None
            self._snapshot_sequence = 0
            self.cellular_peak_group_size = 0
            self.cellular_peak_groups = 0
            self.cellular_peak_bonds = 0
            self._viewport_key = None
            self.recorder = (
                NativeGuiRecorder(self.config, previous_run_id=previous_run_id)
                if self._record
                else None
            )
            self.run_id = (
                self.recorder.run_id if self.recorder else f"native-{time_ns():x}"
            )
            self.error_message = ""
            self.selected_id = None
            self.inspector_scroll = 0
            self._relation_hitboxes.clear()
            self.species_scroll = 0
            self.sliders_scroll = 0
            self.panning = None
            self.camera_x = float(self.config.width // 2)
            self.camera_y = float(self.config.height // 2)
            self.follow_selected = True
            self._save_settings()
            self._request_viewport(force=True)
        except Exception as error:  # noqa: BLE001 - UI reports native initialization failures
            self.error_message = str(error)
            self.paused = True

    def run(self) -> None:
        running = True
        redraw = True
        try:
            self.worker.start()
            self._request_viewport(force=True)
            while running:
                self.clock.tick(self.config.render_fps)
                events = pygame.event.get()
                redraw = redraw or bool(events)
                for event in events:
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        running = self._handle_key(event.key)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self._mouse_down(event.pos)
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (
                        2,
                        3,
                    ):
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
                        redraw = True
                    elif event.type == pygame.MOUSEMOTION and self.dragging:
                        self._update_slider(self.dragging, event.pos[0])
                    elif event.type == pygame.MOUSEWHEEL:
                        if self.show_species_view:
                            self.species_scroll = max(0, self.species_scroll - event.y)
                        elif self.selected_id is not None:
                            self.inspector_scroll = max(
                                0, min(40, self.inspector_scroll - event.y * 3)
                            )
                        else:
                            self._scroll_sliders(-event.y * 3)
                if self._edge_scroll():
                    redraw = True

                self._request_viewport()
                update = self.worker.poll_snapshot(self._snapshot_sequence)
                if update is not None:
                    self._snapshot_sequence, self.snapshot = update
                    self._observe_cellular_snapshot(self.snapshot)
                    if self.recorder is not None:
                        self.recorder.record(
                            self.snapshot, self.worker.status.ticks_per_second
                        )
                    redraw = True
                self._record_applied_config_updates()
                status = self.worker.status
                self.actual_ticks_per_second = status.ticks_per_second
                if status.error:
                    self.error_message = status.error
                    self.paused = True
                if redraw and self.snapshot is not None:
                    self.draw()
                    redraw = False
        finally:
            try:
                self.worker.stop()
                self._record_applied_config_updates()
                if self.recorder is not None:
                    self.recorder.close(self.worker.status)
            finally:
                pygame.quit()

    def _request_viewport(self, *, force: bool = False) -> None:
        bounds = self._visible_tiles()
        key: tuple[object, ...] = (
            *bounds,
            self.show_heat,
            self.show_food,
            self.selected_id,
        )
        if force or key != self._viewport_key:
            self.worker.set_viewport(
                bounds,
                include_heat=self.show_heat,
                include_food=self.show_food,
                selected_id=self.selected_id,
            )
            self._viewport_key = key

    def _handle_key(self, key: int) -> bool:
        pan = 8
        if key == pygame.K_ESCAPE:
            return False
        if key == pygame.K_SPACE:
            self.paused = not self.paused
            self.worker.set_paused(self.paused)
        elif key == pygame.K_n:
            self.worker.step_once()
        elif key == pygame.K_r:
            self.reset()
        elif key == pygame.K_t:
            self.turbo = not self.turbo
            self.worker.set_target_ticks_per_second(
                None if self.turbo else self.config.ticks_per_second
            )
        elif key == pygame.K_h:
            self.show_heat = not self.show_heat
            self._viewport_key = None
        elif key == pygame.K_f:
            self.show_food = not self.show_food
            self._viewport_key = None
        elif key == pygame.K_b:
            self.show_cellular = not self.show_cellular
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
        elif key == pygame.K_j and self.selected_id is not None:
            self._jump_to_relation("offspring_ids")
        elif key == pygame.K_p and self.selected_id is not None:
            self._jump_to_relation("living_parent_ids")
        elif key == pygame.K_g and self.selected_id is not None:
            if not self._jump_to_relation("alliance_ids"):
                self._jump_to_relation("bond_ids")
        elif key == pygame.K_c and self.selected_id is not None:
            self.follow_selected = not self.follow_selected
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.turbo = False
            self.config.ticks_per_second = min(
                2000.0, self.config.ticks_per_second + 25
            )
            self._sync_slider("ticks_per_second")
            self._save_settings()
            self.worker.set_target_ticks_per_second(self.config.ticks_per_second)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.turbo = False
            self.config.ticks_per_second = max(1.0, self.config.ticks_per_second - 25)
            self._sync_slider("ticks_per_second")
            self._save_settings()
            self.worker.set_target_ticks_per_second(self.config.ticks_per_second)
        elif key == pygame.K_LEFTBRACKET:
            self.config.seed -= 1
            self._save_settings()
        elif key == pygame.K_RIGHTBRACKET:
            self.config.seed += 1
            self._save_settings()
        return True

    def _update_slider(self, slider: Slider, x: int) -> None:
        slider.set_from_x(x)
        value = self._apply_slider_value(slider)
        self._save_settings()
        if not slider.live:
            return
        if slider.field == "ticks_per_second":
            self.turbo = False
            self.worker.set_target_ticks_per_second(float(value))
        else:
            self.worker.update_config(**{slider.field: value})

    def _mouse_down(self, position: tuple[int, int]) -> None:
        if position[0] >= self.world_pixels:
            for rect, organism_id in self._relation_hitboxes:
                if rect.collidepoint(position):
                    self._select_organism(organism_id)
                    return
        if (
            self.show_species_view
            and position[0] >= self.world_pixels
            and position[1] >= 272
        ):
            row = self.species_scroll + (position[1] - 272) // 42
            species = self._active_species()
            if 0 <= row < len(species) and self.snapshot is not None:
                species_id = species[row]["species_id"]
                overview = self.snapshot["overview"]
                matches = overview["id"][overview["species_id"] == species_id]
                if len(matches):
                    self.selected_id = int(matches[0])
                    self.show_species_view = False
                    self.inspector_scroll = 0
                    self._viewport_key = None
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
        if (
            self.snapshot is None
            or position[0] >= self.world_pixels
            or position[1] >= self.world_pixels
        ):
            return
        minimap = self._minimap_rect()
        if self._minimap_bounds is not None and minimap.collidepoint(position):
            self._jump_from_minimap(position)
            self.show_species_view = False
            return
        tile_size = self._tile_size()
        world_x = int(self.camera_x + (position[0] - self.world_pixels / 2) / tile_size)
        world_y = int(self.camera_y + (position[1] - self.world_pixels / 2) / tile_size)
        organisms = self.snapshot["organisms"]
        selected = None
        for index, organism_id in enumerate(organisms["id"]):
            ox = int(organisms["x"][index])
            oy = int(organisms["y"][index])
            area = int(organisms["area"][index])
            if any(
                ox + dx == world_x and oy + dy == world_y
                for dx, dy in World.footprint_offsets(area)
            ):
                selected = int(organism_id)
                break
        self.selected_id = selected
        self.inspector_scroll = 0
        self.show_species_view = False
        self._viewport_key = None

    def _active_species(self) -> list[dict[str, Any]]:
        if self.snapshot is None:
            return []
        table = self.snapshot["species"]
        records = [
            {
                "species_id": int(table["species_id"][index]),
                "population": int(table["population"][index]),
                "births": int(table["births"][index]),
                "deaths": int(table["deaths"][index]),
                "created_tick": int(table["created_tick"][index]),
                "origin": str(table["origin"][index]),
                "color": tuple(table["color"][index]),
            }
            for index in range(len(table["species_id"]))
            if int(table["population"][index]) > 0
        ]
        return sorted(
            records,
            key=lambda item: (
                -int(
                    item["origin"] != "founder"
                    and self._tick - item["created_tick"]
                    <= self.config.new_species_marker_ticks
                ),
                -item["created_tick"],
                -item["population"],
                item["species_id"],
            ),
        )

    def _species_colors(self) -> dict[int, Color]:
        return {
            record["species_id"]: record["color"] for record in self._active_species()
        }

    def _selected_index(self) -> int | None:
        if self.snapshot is None or self.selected_id is None:
            return None
        matches = np.flatnonzero(self.snapshot["organisms"]["id"] == self.selected_id)
        return int(matches[0]) if len(matches) else None

    def _relation_ids(self, relation: str) -> list[int]:
        if self.snapshot is None:
            return []
        relations = self.snapshot.get("selected_relations", {})
        return [int(value) for value in relations.get(relation, ())]

    def _select_organism(self, organism_id: int) -> bool:
        if self.snapshot is None:
            return False
        overview = self.snapshot["overview"]
        matches = np.flatnonzero(overview["id"] == organism_id)
        if not len(matches):
            return False
        index = int(matches[0])
        self.selected_id = organism_id
        self.camera_x = float(overview["x"][index])
        self.camera_y = float(overview["y"][index])
        self.follow_selected = True
        self.inspector_scroll = 0
        self.show_species_view = False
        self._relation_hitboxes.clear()
        self._viewport_key = None
        return True

    def _jump_to_relation(self, relation: str) -> bool:
        targets = self._relation_ids(relation)
        return bool(targets) and self._select_organism(targets[0])

    def _draw_world(self) -> None:
        assert self.snapshot is not None
        tile_size = self._tile_size()
        half_view = self.world_pixels / 2
        organisms = self.snapshot["organisms"]
        selected_index = self._selected_index()
        if self.follow_selected and selected_index is not None:
            self.camera_x = float(organisms["x"][selected_index])
            self.camera_y = float(organisms["y"][selected_index])
        x0, y0, x1, y1 = self._visible_tiles()
        pygame.draw.rect(
            self.screen, (20, 24, 32), (0, 0, self.world_pixels, self.world_pixels)
        )

        def screen_xy(x: int, y: int) -> tuple[float, float]:
            return (
                (x - self.camera_x) * tile_size + half_view,
                (y - self.camera_y) * tile_size + half_view,
            )

        heat = self.snapshot["heat"]
        heat_max = max(float(heat["maximum"]), 1e-12)
        for x, y, value in zip(heat["x"], heat["y"], heat["value"]):
            ratio = min(1.0, float(value) / heat_max)
            color = (int(150 * ratio), int(45 * ratio), int(190 * ratio))
            sx, sy = screen_xy(int(x), int(y))
            pygame.draw.rect(self.screen, color, (sx, sy, tile_size, tile_size))

        biodeposits = self.snapshot.get("biodeposits", {})
        biodeposit_density = np.asarray(biodeposits.get("density", ()), dtype=float)
        maximum_biodeposit = float(biodeposit_density.max(initial=1.0))
        for x, y, density in zip(
            biodeposits.get("x", ()),
            biodeposits.get("y", ()),
            biodeposit_density,
        ):
            ratio = min(1.0, float(density) / maximum_biodeposit)
            color = (70 + int(75 * ratio), 54 + int(42 * ratio), 35 + int(25 * ratio))
            sx, sy = screen_xy(int(x), int(y))
            pygame.draw.rect(self.screen, color, (sx, sy, tile_size, tile_size))

        deposits = self.snapshot["deposits"]
        molecule_colors = self.snapshot["molecule_colors"]
        for x, y, molecule_id, units in zip(
            deposits["x"],
            deposits["y"],
            deposits["molecule_id"],
            deposits["units"],
        ):
            square = max(1, min(tile_size, 2 + int(units) // 8))
            sx, sy = screen_xy(int(x), int(y))
            rect = pygame.Rect(
                int(sx + (tile_size - square) / 2),
                int(sy + (tile_size - square) / 2),
                square,
                square,
            )
            pygame.draw.rect(self.screen, molecule_colors[int(molecule_id)], rect)

        corpses = self.snapshot["corpses"]
        for x, y in zip(corpses["x"], corpses["y"]):
            sx, sy = screen_xy(int(x), int(y))
            pygame.draw.line(
                self.screen,
                (100, 92, 86),
                (sx, sy),
                (sx + tile_size, sy + tile_size),
                1,
            )

        colors = self._species_colors()
        if len(organisms["id"]) >= DENSE_RENDER_THRESHOLD and tile_size <= 4:
            self._draw_dense_organisms(organisms, colors, tile_size)
            self._draw_cellular_overlay(organisms, tile_size)
            self._draw_native_minimap()
            return
        for index, organism_id in enumerate(organisms["id"]):
            ox = int(organisms["x"][index])
            oy = int(organisms["y"][index])
            if not (x0 - 16 <= ox < x1 + 16 and y0 - 16 <= oy < y1 + 16):
                continue
            if self.species_colors:
                color = colors.get(int(organisms["species_id"][index]), (180, 180, 180))
            else:
                energy = float(organisms["energy_fraction"][index])
                color = (int(255 * (1 - energy)), int(220 * energy), 90)
            if int(organisms["colony_id"][index]) >= 0:
                color = tuple(min(255, channel + 35) for channel in color)
            area = int(organisms["area"][index])
            for dx, dy in World.footprint_offsets(area):
                x, y = ox + dx, oy + dy
                if x0 <= x < x1 and y0 <= y < y1:
                    sx, sy = screen_xy(x, y)
                    pygame.draw.rect(self.screen, color, (sx, sy, tile_size, tile_size))
            if float(organisms["mana"][index]) > 0.5:
                sx, sy = screen_xy(ox, oy)
                pygame.draw.circle(
                    self.screen,
                    (105, 210, 255),
                    (int(sx + tile_size / 2), int(sy + tile_size / 2)),
                    max(1, tile_size // 3),
                )
            if int(organism_id) == self.selected_id:
                for dx, dy in World.footprint_offsets(area):
                    sx, sy = screen_xy(ox + dx, oy + dy)
                    pygame.draw.rect(
                        self.screen,
                        (255, 255, 255),
                        (sx, sy, tile_size, tile_size),
                        1,
                    )

        self._draw_cellular_overlay(organisms, tile_size)
        self._draw_native_minimap()

    def _draw_cellular_overlay(
        self,
        organisms: dict[str, np.ndarray],
        tile_size: int,
    ) -> None:
        """Make active physical groups visible without changing simulation state."""

        assert self.snapshot is not None
        stats = self.snapshot["stats"]
        if not self.show_cellular or not bool(stats.get("cellular_affordances_enabled", False)):
            return

        half_view = self.world_pixels / 2

        def screen_xy(x: int, y: int) -> tuple[float, float]:
            return (
                (x - self.camera_x) * tile_size + half_view,
                (y - self.camera_y) * tile_size + half_view,
            )

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(0, 0, self.world_pixels, self.world_pixels))
        try:
            bonds = self.snapshot.get("bonds")
            if bonds is not None:
                width = max(2, min(4, tile_size))
                for x_a, y_a, x_b, y_b, strength in zip(
                    bonds["x1"],
                    bonds["y1"],
                    bonds["x2"],
                    bonds["y2"],
                    bonds["strength"],
                ):
                    start = screen_xy(int(x_a), int(y_a))
                    end = screen_xy(int(x_b), int(y_b))
                    start = (int(start[0] + tile_size / 2), int(start[1] + tile_size / 2))
                    end = (int(end[0] + tile_size / 2), int(end[1] + tile_size / 2))
                    strength_value = min(1.0, max(0.0, float(strength)))
                    intensity = 170 + int(80 * strength_value)
                    # Draw the dark underlay after organisms so the link cannot
                    # disappear into a species-colored footprint.
                    pygame.draw.line(self.screen, (8, 35, 38), start, end, width + 2)
                    pygame.draw.line(
                        self.screen,
                        (70, intensity, 190),
                        start,
                        end,
                        width,
                    )

            organism_ids = organisms["id"]
            component_sizes = np.asarray(
                organisms.get(
                    "component_size",
                    np.ones(len(organism_ids), dtype=np.int64),
                ),
                dtype=np.int64,
            )
            component_ids = np.asarray(
                organisms.get(
                    "component_id",
                    np.arange(len(organism_ids), dtype=np.int64),
                ),
                dtype=np.int64,
            )
            labels: dict[int, tuple[int, int, int]] = {}
            for index, size in enumerate(component_sizes):
                if int(size) <= 1:
                    continue
                sx, sy = screen_xy(
                    int(organisms["x"][index]),
                    int(organisms["y"][index]),
                )
                center = (int(sx + tile_size / 2), int(sy + tile_size / 2))
                pygame.draw.circle(
                    self.screen,
                    (255, 224, 86),
                    center,
                    max(3, tile_size + 2),
                    max(1, min(3, tile_size)),
                )
                labels.setdefault(int(component_ids[index]), (center[0], center[1], int(size)))

            if tile_size >= 4:
                for x, y, size in list(labels.values())[:24]:
                    label = self.small_font.render(f"GROUP ×{size}", True, (255, 236, 126))
                    self.screen.blit(label, (x + 4, y - label.get_height() - 2))
        finally:
            self.screen.set_clip(previous_clip)

    def _draw_dense_organisms(
        self,
        organisms: dict[str, np.ndarray],
        colors: dict[int, tuple[int, int, int]],
        tile_size: int,
    ) -> None:
        """Rasterize one zoomed-out marker per organism in a single blit."""

        half_view = self.world_pixels / 2
        xs = np.asarray(organisms["x"], dtype=np.float64)
        ys = np.asarray(organisms["y"], dtype=np.float64)
        screen_x = np.floor((xs - self.camera_x) * tile_size + half_view).astype(
            np.int32
        )
        screen_y = np.floor((ys - self.camera_y) * tile_size + half_view).astype(
            np.int32
        )
        visible = (
            (screen_x < self.world_pixels)
            & (screen_y < self.world_pixels)
            & (screen_x + tile_size > 0)
            & (screen_y + tile_size > 0)
        )
        screen_x = screen_x[visible]
        screen_y = screen_y[visible]

        if self.species_colors:
            species_ids = np.asarray(organisms["species_id"], dtype=np.int64)[visible]
            max_species = max(max(colors, default=0), int(species_ids.max(initial=0)))
            color_table = np.full((max_species + 1, 3), 180, dtype=np.uint8)
            for species_id, color in colors.items():
                color_table[species_id] = color
            rgb = color_table[np.clip(species_ids, 0, max_species)]
        else:
            energy = np.clip(
                np.asarray(organisms["energy_fraction"], dtype=np.float64)[visible],
                0.0,
                1.0,
            )
            rgb = np.column_stack(
                (255 * (1.0 - energy), 220 * energy, np.full_like(energy, 90))
            ).astype(np.uint8)
        colonies = np.asarray(organisms["colony_id"], dtype=np.int64)[visible] >= 0
        if colonies.any():
            rgb[colonies] = np.minimum(rgb[colonies].astype(np.uint16) + 35, 255)

        layer = pygame.Surface(
            (self.world_pixels, self.world_pixels), pygame.SRCALPHA, 32
        )
        pixels = pygame.surfarray.pixels3d(layer)
        alpha = pygame.surfarray.pixels_alpha(layer)
        for dx in range(tile_size):
            pixel_x = screen_x + dx
            for dy in range(tile_size):
                pixel_y = screen_y + dy
                in_bounds = (
                    (pixel_x >= 0)
                    & (pixel_x < self.world_pixels)
                    & (pixel_y >= 0)
                    & (pixel_y < self.world_pixels)
                )
                pixels[pixel_x[in_bounds], pixel_y[in_bounds]] = rgb[in_bounds]
                alpha[pixel_x[in_bounds], pixel_y[in_bounds]] = 255
        del pixels, alpha
        self.screen.blit(layer, (0, 0))

        selected_index = self._selected_index()
        if selected_index is not None:
            selected_x = int(
                (int(organisms["x"][selected_index]) - self.camera_x) * tile_size
                + half_view
            )
            selected_y = int(
                (int(organisms["y"][selected_index]) - self.camera_y) * tile_size
                + half_view
            )
            pygame.draw.rect(
                self.screen,
                (255, 255, 255),
                (selected_x, selected_y, tile_size, tile_size),
                1,
            )

    def _draw_native_minimap(self) -> None:
        assert self.snapshot is not None
        rect = self._minimap_rect()
        overview = self.snapshot["overview"]
        chunks = self.snapshot["chunks"]
        chunk_size = int(chunks["size"])
        overview_x = np.asarray(overview["x"], dtype=np.int64)
        overview_y = np.asarray(overview["y"], dtype=np.int64)
        chunk_x = np.asarray(chunks["x"], dtype=np.int64) * chunk_size
        chunk_y = np.asarray(chunks["y"], dtype=np.int64) * chunk_size
        xs = np.concatenate((overview_x, chunk_x, [int(self.camera_x)]))
        ys = np.concatenate((overview_y, chunk_y, [int(self.camera_y)]))
        pad = 16
        x0, x1 = int(xs.min()) - pad, int(xs.max()) + pad
        y0, y1 = int(ys.min()) - pad, int(ys.max()) + pad
        scale = min(rect.width / max(1, x1 - x0), rect.height / max(1, y1 - y0))
        self._minimap_bounds = (x0, y0, x1, y1, scale, rect.x, rect.y)
        surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surface.fill((13, 16, 24, 210))
        for cx, cy in zip(chunks["x"], chunks["y"]):
            mx = int((int(cx) * chunk_size - x0) * scale)
            my = int((int(cy) * chunk_size - y0) * scale)
            if 0 <= mx < rect.width and 0 <= my < rect.height:
                surface.set_at((mx, my), (70, 76, 90))
        colors = self._species_colors()
        if len(overview_x) >= DENSE_RENDER_THRESHOLD:
            minimap_x = ((overview_x - x0) * scale).astype(np.int32)
            minimap_y = ((overview_y - y0) * scale).astype(np.int32)
            visible = (
                (minimap_x >= 0)
                & (minimap_x < rect.width)
                & (minimap_y >= 0)
                & (minimap_y < rect.height)
            )
            species_ids = np.asarray(overview["species_id"], dtype=np.int64)[visible]
            max_species = max(max(colors, default=0), int(species_ids.max(initial=0)))
            color_table = np.full((max_species + 1, 3), 180, dtype=np.uint8)
            for species_id, color in colors.items():
                color_table[species_id] = color
            rgb = color_table[np.clip(species_ids, 0, max_species)]
            pixels = pygame.surfarray.pixels3d(surface)
            alpha = pygame.surfarray.pixels_alpha(surface)
            pixels[minimap_x[visible], minimap_y[visible]] = rgb
            alpha[minimap_x[visible], minimap_y[visible]] = 255
            del pixels, alpha
        else:
            for x, y, species_id in zip(
                overview["x"], overview["y"], overview["species_id"]
            ):
                mx = int((int(x) - x0) * scale)
                my = int((int(y) - y0) * scale)
                if 0 <= mx < rect.width and 0 <= my < rect.height:
                    surface.set_at(
                        (mx, my), colors.get(int(species_id), (180, 180, 180))
                    )
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
            self.small_font.render("native minimap", True, (150, 163, 184)),
            (rect.x + 4, rect.y + 2),
        )

    def _draw_panel(self) -> None:
        assert self.snapshot is not None
        self._relation_hitboxes.clear()
        panel_x = self.world_pixels
        pygame.draw.rect(
            self.screen,
            (24, 29, 41),
            (panel_x, 0, self.screen.get_width() - panel_x, self.screen.get_height()),
        )
        stats = self.snapshot["stats"]
        season = self.snapshot["season"]
        status = self.worker.status
        target = "MAX" if self.turbo else f"{self.config.ticks_per_second:g}"
        engine_text = (
            f"{self.snapshot.get('scheduler', 'serial-v2')} "
            f"{self.snapshot.get('effective_parallel_workers', 1)}w"
        )
        cellular_enabled = bool(stats["cellular_affordances_enabled"])
        cellular_text = (
            f"CELLULAR ON  groups {stats['bond_components']} "
            f"max {stats['largest_bond_component']} peak {self.cellular_peak_group_size} "
            f"formed {stats['bond_formations']}"
            if cellular_enabled
            else "CELLULAR OFF — no joined groups can form"
        )
        season_text = (
            f"season {season['index']}  resources ×{season['resource_charge_multiplier']:.2f} "
            f"decay ×{season['decomposition_multiplier']:.2f}"
            if season["enabled"]
            else "seasons disabled"
        )
        lines = [
            "EMERGENT ORGANISMS — RUST",
            f"seed {self.config.seed}   tick {self._tick}   run {self.run_id[-8:]}",
            f"population {self.snapshot['population']} / born {stats['births']}",
            f"species {sum(item['population'] > 0 for item in self._active_species())}   deaths {stats['deaths']}",
            f"sexual events {stats['sexual_reproduction_events']}   asexual {stats['asexual_reproduction_events']}",
            f"magic {stats['magic_casts']}   attacks {stats['attacks']}",
            cellular_text,
            season_text,
            f"ticks/s {self.actual_ticks_per_second:.1f} actual / {target} target",
            (
                f"state {'PAUSED' if self.paused else 'RUNNING'}   batch {status.batch_ticks}   {engine_text}"
                + (
                    f"   bio {stats['biodeposit_positions']}"
                    if stats.get("biodeposits_enabled", False)
                    else ""
                )
            ),
        ]
        y = 18
        for index, line in enumerate(lines):
            if index == 0:
                color: Color = (242, 245, 250)
            elif index == 6:
                color = (95, 240, 190) if cellular_enabled else (255, 120, 120)
            else:
                color = (190, 201, 218)
            self.screen.blit(self.font.render(line, True, color), (panel_x + 20, y))
            y += 23

        if self.show_species_view:
            self._draw_native_species(panel_x)
        elif self.selected_id is not None and self._selected_index() is not None:
            self._draw_native_inspector(panel_x, self._selected_index())
        else:
            self.screen.blit(
                self.small_font.render(
                    "Click an organism to inspect it. T toggles MAX speed.",
                    True,
                    (205, 211, 225),
                ),
                (panel_x + 20, 242),
            )
            viewport = self._slider_viewport()
            max_scroll = self._max_sliders_scroll()
            self.sliders_scroll = min(self.sliders_scroll, max_scroll)
            previous_clip = self.screen.get_clip()
            self.screen.set_clip(viewport)
            for slider in self.sliders:
                rect = slider.rect.move(0, -self.sliders_scroll)
                if rect.bottom >= viewport.top and rect.top <= viewport.bottom:
                    slider.draw(self.screen, self.small_font, rect)
            self.screen.set_clip(previous_clip)

        settings = self.settings_path.name if self.settings_path else "autosave off"
        message = self.error_message or f"settings {settings} | B groups | T max | R apply/reset"
        color = (255, 105, 105) if self.error_message else (150, 163, 184)
        self.screen.blit(
            self.small_font.render(message[:60], True, color), (panel_x + 20, 736)
        )
        help_lines = (
            "H heat  F food  B groups  S colors  V species",
            "RMB/edges pan  C follow  J child  P parent",
            ", . zoom 1–64   G joined   [ ] reset seed",
        )
        for index, line in enumerate(help_lines):
            self.screen.blit(
                self.small_font.render(line, True, (130, 141, 160)),
                (panel_x + 20, 756 + index * 16),
            )

    def _draw_native_species(self, panel_x: int) -> None:
        records = self._active_species()
        self.screen.blit(
            self.font.render(f"ACTIVE SPECIES ({len(records)})", True, (116, 207, 255)),
            (panel_x + 20, 242),
        )
        viewport = pygame.Rect(panel_x + 12, 272, self.config.panel_width - 24, 458)
        row_height = 42
        visible_rows = max(1, viewport.height // row_height)
        self.species_scroll = min(
            self.species_scroll, max(0, len(records) - visible_rows)
        )
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(viewport)
        for visible_index, species in enumerate(records[self.species_scroll :]):
            y = viewport.y + visible_index * row_height
            if y > viewport.bottom:
                break
            pygame.draw.rect(
                self.screen,
                (34, 40, 54),
                (panel_x + 17, y + 2, self.config.panel_width - 34, row_height - 4),
            )
            pygame.draw.rect(
                self.screen, species["color"], (panel_x + 24, y + 9, 18, 18)
            )
            self.screen.blit(
                self.small_font.render(
                    f"Species {species['species_id']} {species['origin'].upper()}  pop {species['population']}",
                    True,
                    (232, 236, 244),
                ),
                (panel_x + 49, y + 7),
            )
            self.screen.blit(
                self.small_font.render(
                    f"created {species['created_tick']}  births {species['births']} deaths {species['deaths']}",
                    True,
                    (174, 185, 204),
                ),
                (panel_x + 49, y + 23),
            )
        self.screen.set_clip(previous_clip)

    def _draw_native_inspector(self, panel_x: int, index: int | None) -> None:
        if index is None or self.snapshot is None:
            return
        organisms = self.snapshot["organisms"]
        action_code = int(organisms["last_action"][index])
        last_action_names = self.snapshot.get("last_action_names")
        if last_action_names is not None and 0 <= action_code < len(last_action_names):
            action = last_action_names[action_code]
        else:
            action_names = self.snapshot["action_names"]
            action = (
                action_names[action_code - 1]
                if 1 <= action_code <= len(action_names)
                else "born/dead"
            )
        parent_ids = self._relation_ids("parent_ids")
        living_parent_ids = self._relation_ids("living_parent_ids")
        offspring_ids = self._relation_ids("offspring_ids")
        alliance_ids = self._relation_ids("alliance_ids")
        bond_ids = self._relation_ids("bond_ids")
        lines: list[tuple[str, int | None]] = [
            (f"ORGANISM #{int(organisms['id'][index])}", None),
            (
                f"species {int(organisms['species_id'][index])}  lineage {int(organisms['lineage_id'][index])}",
                None,
            ),
            (
                f"age {self._tick - int(organisms['birth_tick'][index])}  generation {int(organisms['generation'][index])}",
                None,
            ),
            (
                f"position {int(organisms['x'][index])},{int(organisms['y'][index])}  area {int(organisms['area'][index])}",
                None,
            ),
            (
                f"energy {float(organisms['energy_fraction'][index]):.1%}  mana {float(organisms['mana'][index]):.3g}",
                None,
            ),
            (
                f"integrity {float(organisms['integrity'][index]):.2f}/{float(organisms['max_integrity'][index]):.2f}",
                None,
            ),
            (
                f"toxin {float(organisms['toxin_load'][index]):.3g}/{float(organisms['toxin_tolerance'][index]):.3g}",
                None,
            ),
            (f"last action {action}", None),
            (
                f"offspring {int(organisms['offspring_count'][index])}  kills {int(organisms['kills'][index])}",
                None,
            ),
            (
                f"modules {int(organisms['module_count'][index])} expressed {int(organisms['expressed_module_count'][index])}",
                None,
            ),
            (
                f"compartment tags {int(organisms['compartment_count'][index])} bonds {int(organisms['bond_degree'][index])}",
                None,
            ),
            (
                f"component #{int(organisms['component_id'][index])} size {int(organisms['component_size'][index])}",
                None,
            ),
            (
                f"internal guests {int(organisms['internal_guest_count'][index])}",
                None,
            ),
        ]
        if len(parent_ids) == 2:
            lines.append((f"parents joined: #{parent_ids[0]} + #{parent_ids[1]}", None))
        elif parent_ids:
            lines.append((f"asexual parent: #{parent_ids[0]}", None))
        else:
            lines.append(("founder: no parents", None))
        if offspring_ids:
            lines.extend(
                [
                    (f"living new organisms: {len(offspring_ids)}", None),
                    (
                        f"[JUMP] newest offspring #{offspring_ids[0]} (J)",
                        offspring_ids[0],
                    ),
                ]
            )
        if living_parent_ids:
            lines.append(
                (
                    f"[JUMP] living parent #{living_parent_ids[0]} (P)",
                    living_parent_ids[0],
                )
            )
        if alliance_ids:
            lines.extend(
                [
                    (f"joined/allied with {len(alliance_ids)} living", None),
                    (f"[JUMP] joined organism #{alliance_ids[0]} (G)", alliance_ids[0]),
                ]
            )
        if bond_ids:
            lines.extend(
                [
                    (f"physically bonded with {len(bond_ids)} living", None),
                    (f"[JUMP] bonded organism #{bond_ids[0]}", bond_ids[0]),
                ]
            )
        lines.extend(
            [
                ("", None),
                ("Relationships list living jump targets only.", None),
                ("Click a cyan JUMP line or use J/P/G.", None),
            ]
        )
        viewport = pygame.Rect(panel_x + 12, 258, self.config.panel_width - 24, 472)
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(viewport)
        y = viewport.y - self.inspector_scroll * 17
        for line, target_id in lines:
            if y + 17 >= viewport.top and y <= viewport.bottom:
                color = (116, 207, 255) if target_id is not None else (205, 211, 225)
                rendered = self.small_font.render(line, True, color)
                position = (panel_x + 20, y)
                if target_id is not None:
                    hitbox = rendered.get_rect(topleft=position).inflate(8, 3)
                    pygame.draw.rect(self.screen, (34, 51, 68), hitbox, border_radius=3)
                    self._relation_hitboxes.append((hitbox, target_id))
                self.screen.blit(rendered, position)
            y += 17
        self.screen.set_clip(previous_clip)


__all__ = ["NativeApp"]
