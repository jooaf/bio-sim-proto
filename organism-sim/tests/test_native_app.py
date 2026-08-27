from __future__ import annotations

from time import monotonic, sleep

import numpy as np
import pygame

from organism_sim.config import SimulationConfig
from organism_sim.config_io import build_config, load_config_file
from organism_sim.native_app import NativeApp


def test_native_app_draws_worker_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    app = NativeApp(
        SimulationConfig(
            founder_count=40,
            founder_archetype_count=4,
            audit_every=0,
        ),
        record=False,
    )
    try:
        app.worker.start()
        app._request_viewport(force=True)
        deadline = monotonic() + 3.0
        update = None
        while monotonic() < deadline and update is None:
            update = app.worker.poll_snapshot(app._snapshot_sequence)
            sleep(0.01)
        assert update is not None
        app._snapshot_sequence, app.snapshot = update

        app.draw()

        assert app.snapshot["population"] > 0
        assert app._tick >= 0
        assert pygame.display.get_surface() is app.screen
    finally:
        app.worker.stop()
        pygame.quit()


def test_native_sliders_update_pending_config_and_saved_settings(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    settings_path = tmp_path / "gui-settings.json"
    app = NativeApp(
        SimulationConfig(audit_every=0),
        record=False,
        settings_path=settings_path,
    )
    try:
        founders = next(
            slider for slider in app.sliders if slider.field == "founder_count"
        )
        app._update_slider(founders, founders.rect.right)
        assert app.config.founder_count == 5000

        season_min = next(
            slider for slider in app.sliders if slider.field == "season_duration_min"
        )
        app._update_slider(season_min, season_min.rect.right)
        assert app.config.season_duration_min == 5000
        assert app.config.season_duration_max == 5000

        app.sliders_scroll = app._max_sliders_scroll()
        last_slider = app.sliders[-1]
        visible_rect = last_slider.rect.move(0, -app.sliders_scroll)
        app._mouse_down(visible_rect.center)
        assert app.dragging is last_slider

        app._handle_key(pygame.K_RIGHTBRACKET)
        simulation_values, _ = load_config_file(settings_path)
        restored = build_config(simulation_values)
        assert restored.founder_count == 5000
        assert restored.season_duration_min == 5000
        assert restored.season_duration_max == 5000
        assert restored.seed == app.config.seed
    finally:
        pygame.quit()


def test_native_zoom_uses_extended_discrete_range(monkeypatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    app = NativeApp(SimulationConfig(tile_pixels=6, audit_every=0), record=False)
    try:
        app._change_zoom(-1)
        assert app._tile_size() == 4
        app.config.tile_pixels = 1
        app._change_zoom(-1)
        assert app._tile_size() == 1
        app.config.tile_pixels = 64
        app._change_zoom(1)
        assert app._tile_size() == 64
    finally:
        pygame.quit()


def test_native_relationship_jump_selects_living_target(monkeypatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    app = NativeApp(SimulationConfig(audit_every=0), record=False)
    app.snapshot = {
        "overview": {
            "id": np.array([1, 9], dtype=np.uint32),
            "x": np.array([3, 41], dtype=np.int64),
            "y": np.array([5, 43], dtype=np.int64),
        },
        "selected_relations": {
            "offspring_ids": np.array([9], dtype=np.uint32),
        },
    }
    app.selected_id = 1
    try:
        assert app._jump_to_relation("offspring_ids") is True
        assert app.selected_id == 9
        assert (app.camera_x, app.camera_y) == (41.0, 43.0)
        assert app.follow_selected is True
        assert app._jump_to_relation("living_parent_ids") is False
    finally:
        pygame.quit()


def test_dense_native_renderer_batches_unknown_species(monkeypatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    app = NativeApp(SimulationConfig(audit_every=0), record=False)
    count = 10_000
    organisms = {
        "id": np.arange(1, count + 1, dtype=np.uint32),
        "x": np.arange(count, dtype=np.int64) % 96,
        "y": np.arange(count, dtype=np.int64) // 96 % 96,
        "species_id": np.full(count, 999, dtype=np.int64),
        "energy_fraction": np.full(count, 0.5),
        "colony_id": np.full(count, -1, dtype=np.int64),
    }
    try:
        app.screen.fill((0, 0, 0))
        app._draw_dense_organisms(organisms, {1: (255, 0, 0)}, tile_size=2)
        pixels = pygame.surfarray.array3d(app.screen)
        assert np.any(pixels[: app.world_pixels, : app.world_pixels] != 0)
    finally:
        pygame.quit()
