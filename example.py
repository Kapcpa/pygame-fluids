import sys

import pygame
from pygame.math import Vector2

import water


def render_text(surface, text, font, pos, color=(255, 255, 255)):
	text_surface = font.render(text, True, color)
	surface.blit(text_surface, pos)


def main():
	pygame.init()

	pygame.display.set_caption("Pygame Fluids Example")
	clock = pygame.Clock()
	screen = pygame.display.set_mode((1100, 600), pygame.DOUBLEBUF)
	font = pygame.font.SysFont("Courier New", 16, bold=True)

	tile = 16
	grid_w, grid_h = 50, 35
	scroll = Vector2(grid_w * tile - screen.width - 250, grid_h * tile - screen.height) // 2
	selected_tiles = set()

	paused = False
	debug_mode = False

	# Initializing the fluid
	water_system = water.Water(grid_w, grid_h, tile)

	# Building a bounding box
	# update_fluid_structure is set to False within the for loops to save up on computation
	for sx in range(grid_w):
		water_system.simulation.set_wall(sx, 0, True, False)
		water_system.simulation.set_wall(sx, grid_h - 1, True, False)
	for sy in range(grid_h):
		water_system.simulation.set_wall(0, sy, True, False)
		water_system.simulation.set_wall(grid_w - 1, sy, True, False)
	water_system.simulation.update_fluid_structure()

	while True:
		dt = clock.tick(60) / 1000.0
		dt = min(dt, 0.1)

		mx, my = pygame.mouse.get_pos()
		world_mx = int((mx + scroll.x) / tile)
		world_my = int((my + scroll.y) / tile)

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				sys.exit(0)

			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_SPACE:
					paused = not paused
				elif event.key == pygame.K_d:
					debug_mode = not debug_mode
				elif event.key == pygame.K_s:
					# Place a permanent water source at mouse location
					water_system.add_water_source(mx + scroll.x, my + scroll.y, 1024.0)
				elif event.key == pygame.K_c:
					# Clear permanent water sources
					water_system.clear_sources()

		mouse_pressed = pygame.mouse.get_pressed()

		if mouse_pressed[0]:
			if (world_mx, world_my) not in selected_tiles:
				selected_tiles.add((world_mx, world_my))
				water_system.simulation.flip_wall(world_mx, world_my)
		else:
			selected_tiles.clear()

		if mouse_pressed[2]:
			water_system.simulation.add_fluid(world_mx, world_my, 512.0, dt)

		# update

		if not paused:
			water_system.update(dt)

		# draw

		screen.fill((20, 20, 20))

		for y in range(water_system.simulation.height):
			for x in range(water_system.simulation.width):
				if water_system.simulation.wall[y][x]:
					pygame.draw.rect(screen, (80, 80, 80), (x * tile - scroll.x, y * tile - scroll.y, tile, tile))
					pygame.draw.rect(screen, (100, 100, 100), (x * tile - scroll.x, y * tile - scroll.y, tile, tile), 1)

		if debug_mode:
			for x in range(water_system.simulation.width):
				for col in water_system.simulation.columns[x]:
					if not col.empty:
						rect_x = x * tile - scroll.x
						rect_y = col.fluid * tile - scroll.y
						rect_h = col.depth * tile
						pygame.draw.rect(screen, (0, 100, 255, 128), (rect_x, rect_y, tile, rect_h))
		else:
			water_system.draw(screen, scroll)

		ui_texts = [
			f"FPS: {int(clock.get_fps())}",
			f"Status: {'PAUSED' if paused else 'RUNNING'}",
			f"View: {'DEBUG' if debug_mode else 'RENDER'}",
			"--- Controls ---",
			"Left Click : Toggle Wall",
			"Right Click : Pour Water",
			"[S] : Place Water Source",
			"[C] : Clear Sources",
			"[SPACE] : Pause/Resume",
			"[D] : Toggle Debug View",
		]

		for i, text in enumerate(ui_texts):
			render_text(screen, text, font, (10, 10 + (i * 20)))

		pygame.display.flip()


if __name__ == "__main__":
	main()