"""
Water Visuals

This is example module of how the Fluid class should be used - it wraps the core
Fluid physics and adds visual flare like waterfalls and foam particles on top.

Public Methods:

- submerged(x, y): Returns True if the given world coordinate is underwater.
- surface_level(x, y): Returns the Y coordinate of the water surface at a given world X.
- near_surface(x, y, threshold): Checks if a point is close to the water surface.
- add_force(x, y, strength): Applies force to the fluid surface.
- add_water_source(x, y, amount): Creates a constant inflow of water every frame.
- clear_sources(): Clears water sources
"""

from __future__ import annotations
import math
import random
import pygame
from pygame.math import Vector2
import fluid


gravity = 9.0
water_drag = 6.0


def damp(value: float, damping: float, dt: float) -> float:
	return value * math.exp(-damping * dt)


class FoamParticle:
	def __init__(self, pos: Vector2 | tuple[float, float], velocity: Vector2 | tuple[float, float], lifetime: float):
		self.pos = Vector2(pos)
		self.velocity = Vector2(velocity)

		self.lifetime = lifetime
		self.max_lifetime = lifetime
		self.size = random.uniform(4.0, 6.0)

	def update(self, simulation: fluid.Fluid, dt: float):
		self.lifetime -= dt

		self.pos += self.velocity * dt
		self.velocity.y += simulation.tile * gravity * dt

		grid_x = int(self.pos.x / simulation.tile)
		grid_y = int(self.pos.y / simulation.tile)
		if not (0 <= grid_x < simulation.width):
			return

		if not simulation.columns[grid_x] or simulation.wall[grid_y][grid_x]:
			self.lifetime = 0.0
			return

		for column in simulation.columns[grid_x]:
			if column.ceiling <= self.pos.y / simulation.tile <= column.floor:
				if column.empty:
					self.lifetime = 0.0
					break

				surface = column.fluid * simulation.tile
				if self.pos.y > surface:
					buoyancy = 64.0 * (surface - self.pos.y)
					self.velocity.y += buoyancy * dt

					column_flux = sum(pipe.flux for pipe in column.pipes) / len(column.pipes) if column.pipes else 0.0
					self.velocity.x += column_flux * dt

					self.velocity.x = damp(self.velocity.x, water_drag, dt)
					self.velocity.y = damp(self.velocity.y, water_drag, dt)

				break

	def draw(self, surf: pygame.Surface, scroll: Vector2):
		if self.lifetime <= 0:
			return

		size = self.size * self.lifetime / self.max_lifetime
		pygame.draw.rect(surf, (168, 181, 178), (self.pos - scroll - Vector2(size / 2), (size, size)))


class Waterfall:
	def __init__(self, x: int, simulation: fluid.Fluid, pipe: fluid.FluidPipe, reverse: bool):
		self.wave_chance = 0.5
		self.particles = 4
		self.timer, self.frequency = random.uniform(0.0, 1.0), 0.25

		self.rect = pygame.Rect(0.0, 0.0, 0.0, 0.0)
		self.set_rect(x, simulation, pipe, reverse)

	def set_rect(self, x: int, simulation: fluid.Fluid, pipe: fluid.FluidPipe, reverse: bool):
		if reverse:
			a, b = pipe.b, pipe.a
			flux = abs(pipe.flux)
		else:
			a, b = pipe.a, pipe.b
			flux = pipe.flux

		edge_x = (x + 1) * simulation.tile
		top = a.fluid * simulation.tile
		bottom = b.fluid * simulation.tile

		thickness = ((flux ** 2) / (simulation.gravity * simulation.tile)) ** (1 / 3)

		self.rect = pygame.Rect(edge_x - thickness if reverse else edge_x, top, thickness, bottom - top + 1)

	def update(self, water: Water, dt: float):
		self.timer -= 1.0 * dt
		if self.timer > 0:
			return

		self.timer = self.frequency

		if random.random() < self.wave_chance:
			water.add_force(self.rect.centerx, self.rect.bottom, random.randint(5, 15))

		for _ in range(self.particles):
			pos = (self.rect.centerx + random.uniform(-self.rect.width, self.rect.width), self.rect.bottom)
			velocity = Vector2(random.uniform(-1.0, 1.0), random.uniform(-2.0, -0.5)) * water.simulation.tile
			lifetime = random.uniform(0.5, 2.0)

			water.particles.append(FoamParticle(pos, velocity, lifetime))

	def draw(self, surf: pygame.Surface, scroll: Vector2):
		pygame.draw.rect(surf, (37, 58, 94), (self.rect.topleft - scroll, self.rect.size))

		pygame.draw.line(surf, (79, 143, 186), self.rect.topleft - scroll, self.rect.topright - scroll, 2)
		pygame.draw.line(surf, (60, 94, 139), self.rect.topleft - scroll + Vector2(0, 1), self.rect.topright - scroll + Vector2(0, 1), 1)


class Water:
	def __init__(self, width: int, height: int, tile: float):
		self.simulation = fluid.Fluid(width, height, tile, gravity)
		self.water_sources: list[tuple[int, int, float]] = []

		self.waterfall_threshold = 1.0
		self.waterfalls: dict[fluid.FluidPipe, Waterfall] = {}

		self.particles: list[FoamParticle] = []

	def submerged(self, x: float, y: float) -> bool:
		grid_x = int(x / self.simulation.tile)
		grid_y = y / self.simulation.tile

		if not (0 <= grid_x < self.simulation.width):
			return False

		for column in self.simulation.columns[grid_x]:
			if column.fluid <= grid_y <= column.floor:
				return True

		return False

	def surface_level(self, x: float, y: float) -> float:
		grid_x = int(x / self.simulation.tile)
		grid_y = y / self.simulation.tile

		for column in self.simulation.columns[grid_x]:
			if column.empty or not (column.ceiling <= grid_y <= column.floor):
				continue

			return column.fluid * self.simulation.tile
		return None

	def near_surface(self, x: float, y: float, threshold: float = 16.0) -> bool:
		grid_x = int(x / self.simulation.tile)
		grid_y = y / self.simulation.tile
		grid_threshold = threshold / self.simulation.tile

		if not (0 <= grid_x < self.simulation.width):
			return False

		for column in self.simulation.columns[grid_x]:
			if column.empty or abs(grid_y - column.fluid) > grid_threshold:
				continue

			if column.ceiling - grid_threshold <= grid_y <= column.floor + grid_threshold:
				return True

		return False

	def add_force(self, x: float, y: float, strength: float):
		grid_x = int(x / self.simulation.tile)
		grid_y = y / self.simulation.tile

		if not (0 <= grid_x < self.simulation.width):
			return

		for column in self.simulation.columns[grid_x]:
			if column.empty or not (column.ceiling <= grid_y <= column.floor):
				continue

			for pipe in column.pipes:
				if pipe.a == column:
					pipe.flux += strength
				elif pipe.b == column:
					pipe.flux -= strength

			particles = int(abs(strength) // 4)
			for _ in range(particles):
				pos = (x + random.uniform(-self.simulation.tile, self.simulation.tile) / 2, column.fluid * self.simulation.tile)
				velocity = Vector2(random.uniform(-1.0, 1.0), random.uniform(-2.0, -0.5)) * self.simulation.tile
				lifetime = random.uniform(0.5, 2.0)

				self.particles.append(FoamParticle(pos, velocity, lifetime))

			break

	def add_water_source(self, x: float, y: float, amount: float):
		self.water_sources.append((int(x / self.simulation.tile), int(y / self.simulation.tile), amount))

	def clear_sources(self):
		self.water_sources.clear()

	def update(self, dt: float):
		for x, y, amount in self.water_sources:
			self.simulation.add_fluid(x, y, amount, dt)

		self.simulation.update(dt)

		active_waterfalls: dict[fluid.FluidPipe, Waterfall] = {}
		for x in range(self.simulation.width - 1):
			for column in self.simulation.columns[x]:
				for pipe in column.pipes:
					if pipe.a != column:
						continue

					is_waterfall, reverse = False, False
					if pipe.flux > 0.1 and column.floor < pipe.b.fluid - self.waterfall_threshold / self.simulation.tile:
						is_waterfall, reverse = True, False
					elif pipe.flux < -0.1 and pipe.b.floor < column.fluid - self.waterfall_threshold / self.simulation.tile:
						is_waterfall, reverse = True, True

					if is_waterfall:
						waterfall = Waterfall(x, self.simulation, pipe, reverse)
						if pipe in self.waterfalls:
							waterfall = self.waterfalls[pipe]
							waterfall.set_rect(x, self.simulation, pipe, reverse)

						active_waterfalls[pipe] = waterfall
		self.waterfalls = active_waterfalls

		for waterfall in self.waterfalls.values():
			waterfall.update(self, dt)

		for particle in self.particles:
			particle.update(self.simulation, dt)

		self.particles = [particle for particle in self.particles if particle.lifetime > 0]

	def draw(self, surf: pygame.Surface, scroll: Vector2):
		for waterfall in self.waterfalls.values():
			waterfall.draw(surf, scroll)

		for surface, polygon in self.simulation.fluid_polygons(surf.size, scroll):
			pygame.draw.polygon(surf, (37, 58, 94), polygon)

			pygame.draw.lines(surf, (79, 143, 186), False, surface, 2)
			pygame.draw.lines(surf, (60, 94, 139), False, [(point[0], point[1] + 1) for point in surface], 1)

		for particle in self.particles:
			particle.draw(surf, scroll)
