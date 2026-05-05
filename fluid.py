"""
Core Fluid Module

A high-performance, grid-based shallow water simulation utilizing a Pipe-Model
approach. It represents fluid as 1D vertical columns that communicate volume
through virtual horizontal pipes, allowing for pressurized flow and fast computation.

Reference: https://diglib.eg.org/server/api/core/bitstreams/47f5228c-6f1c-4afb-ab80-b98c44575bc8/content

Public API:

- Fluid(width, height, tile): Initializes the simulation grid.
- set_wall(x, y, solid, update_fluid_structure): Updates the collision grid and rebuilds structures.
	The bool update_fluid_structure can be set to False to delay the update and should be used if you
	know you'll be adding many walls.
- flip_wall(x, y): Toggles a specific tile between solid/empty.
- add_fluid(x, y, amount, dt): Injects water into the simulation at the given grid coordinates.
- update_fluid_structure(): Updates the columns based on current wall structure.
- update(dt): Steps the simulation physics forward.
- fluid_polygons(surface_size, scroll): Returns raw vertex lists for rendering the fluid surface.
"""

from __future__ import annotations
from collections import deque


class FluidPipe:
	"""Internal class representing a virtual connection between fluid columns."""
	def __init__(self, a: FluidColumn, b: FluidColumn):
		self.a = a
		self.b = b

		self.flux = 0.0


class FluidColumn:
	"""Internal class representing a column that can hold fluid."""
	def __init__(self, floor: float, ceiling: float, fluid: float = None):
		self.floor = floor
		self.ceiling = ceiling
		self.fluid = fluid if fluid is not None else floor

		self.pipes: list[FluidPipe] = []

		self.inflow = 0.0
		self.outflow = 0.0
		self.volume_change = 0.0

	@property
	def depth(self) -> float:
		return self.floor - self.fluid

	@property
	def space(self) -> float:
		return self.fluid - self.ceiling

	@property
	def flooded(self) -> bool:
		return self.space <= 0.01

	@property
	def empty(self) -> bool:
		return self.depth <= 0.01


class Fluid:
	"""Main simulation class"""
	def __init__(self, width: int, height: int, tile: float, gravity: float = 9.81, flux_retained: float = 0.5, viscosity: float = 0.01):
		self.width = width
		self.height = height
		self.tile = tile

		self.wall: list[list[bool]] = [[False for _ in range(self.width)] for _ in range(self.height)]

		self.columns: list[list[FluidColumn]] = [[] for _ in range(self.width)]
		self.pipes: list[FluidPipe] = []
		self.extended_pipes: list[FluidPipe] = []
		self.update_fluid_structure()

		self.gravity = gravity
		self.flux_retained = flux_retained
		self.viscosity = viscosity

	def update_fluid_structure(self):
		"""Rebuilds columns and pipes based on the current wall layout."""
		for x in range(self.width):
			old_columns = self.columns[x]
			new_columns = []

			empty = False
			ceiling = 0.0

			for y in range(self.height):
				if not self.wall[y][x] and not empty:
					empty = True
					ceiling = float(y)
				elif self.wall[y][x] and empty:
					empty = False
					floor = float(y)
					new_columns.append(FluidColumn(floor, ceiling, floor))

			if empty:
				floor = float(self.height)
				new_columns.append(FluidColumn(floor, ceiling, fluid=floor))

			for new_column in new_columns:
				depth = 0.0

				for old_column in old_columns:
					overlap_top = max(old_column.fluid, new_column.ceiling)
					overlap_bottom = min(old_column.floor, new_column.floor)

					if overlap_bottom > overlap_top:
						depth += (overlap_bottom - overlap_top)

				new_column.fluid = new_column.floor - min(depth, new_column.floor - new_column.ceiling)

			self.columns[x] = new_columns

		self.pipes = []
		for x in range(self.width - 1):
			for a in self.columns[x]:
				for b in self.columns[x + 1]:
					if a.floor > b.ceiling and a.ceiling < b.floor:
						pipe = FluidPipe(a, b)

						self.pipes.append(pipe)
						a.pipes.append(pipe)
						b.pipes.append(pipe)

	def update_extended_pipes(self):
		"""Internal physics step: Calculates pressure links through completely flooded columns."""
		pipes = []

		for x in range(self.width):
			for column in self.columns[x]:
				if column.flooded:
					continue

				for pipe in column.pipes:
					if pipe.a != column or not pipe.b.flooded:
						continue

					end = None
					current_flooded = pipe.b

					while current_flooded is not None:
						next_flooded = None

						for next_pipe in current_flooded.pipes:
							if next_pipe.a != current_flooded:
								continue

							if next_pipe.b.flooded:
								next_flooded = next_pipe.b
								break

							end = next_pipe.b
							break

						if end:
							break

						current_flooded = next_flooded

					if not end:
						continue

					existing_pipe = next((ep for ep in self.extended_pipes if ep.a == column and ep.b == end), None)
					if existing_pipe:
						pipes.append(existing_pipe)
						continue

					pipes.append(FluidPipe(column, end))

		self.extended_pipes = pipes

	def set_wall(self, x: int, y: int, value: bool, update_fluid_structure: bool = True):
		if 0 <= x < self.width and 0 <= y < self.height:
			self.wall[y][x] = value

			if update_fluid_structure:
				self.update_fluid_structure()

	def flip_wall(self, x: int, y: int):
		if 0 <= x < self.width and 0 <= y < self.height:
			self.set_wall(x, y, not self.wall[y][x])

	def add_fluid(self, x: int, y: int, amount: float, dt: float):
		if not (0 <= x < self.width and 0 <= y < self.height) or self.wall[y][x]:
			return

		for column in self.columns[x]:
			if not (column.ceiling <= y <= column.floor):
				continue

			target_column = column
			if target_column.flooded:
				queue = deque([target_column])
				visited = {target_column}
				found_open = None

				while queue:
					current = queue.popleft()
					if not current.flooded:
						found_open = current
						break

					for pipe in current.pipes:
						neighbor = pipe.b if pipe.a == current else pipe.a
						if neighbor not in visited:
							visited.add(neighbor)
							queue.append(neighbor)

				if found_open:
					target_column = found_open
				else:
					return

			height_change = (amount * dt) / (self.tile ** 2)
			target_column.fluid = max(target_column.fluid - height_change, target_column.ceiling)
			break

	def update(self, dt: float):
		zeta = self.flux_retained ** dt
		flow_acceleration = dt * self.gravity * self.tile

		self.update_extended_pipes()
		pipes = self.pipes + self.extended_pipes

		for pipe in pipes:
			pressure_difference = (pipe.b.fluid - pipe.a.fluid) * self.tile
			pipe.flux = (zeta * pipe.flux) + (flow_acceleration * pressure_difference)

			h = pipe.a.depth if pipe.flux > 0 else pipe.b.depth
			h *= self.tile
			viscosity_factor = (h ** 2) / (h ** 2 + 3 * dt * self.viscosity)
			if h <= 0.01:
				viscosity_factor = 0.0

			pipe.flux *= viscosity_factor

		for x in range(self.width):
			for column in self.columns[x]:
				column.inflow = 0.0
				column.outflow = 0.0
				column.volume_change = 0.0

		for pipe in pipes:
			volume = pipe.flux * dt

			if volume > 0:
				pipe.a.outflow += volume
				pipe.b.inflow += volume
			elif volume < 0:
				pipe.b.outflow += abs(volume)
				pipe.a.inflow += abs(volume)

		for pipe in pipes:
			volume = pipe.flux * dt
			if volume == 0:
				continue

			scale = 1.0
			if volume > 0:
				max_out = pipe.a.depth * self.tile
				if pipe.a.outflow > max_out:
					scale = min(scale, max_out / pipe.a.outflow)

				max_in = pipe.b.space * self.tile
				if pipe.b.inflow > max_in:
					scale = min(scale, max_in / pipe.b.inflow)
			elif volume < 0:
				max_out = pipe.b.depth * self.tile
				if pipe.b.outflow > max_out:
					scale = min(scale, max_out / pipe.b.outflow)

				max_in = pipe.a.space * self.tile
				if pipe.a.inflow > max_in:
					scale = min(scale, max_in / pipe.a.inflow)

			pipe.flux *= scale
			volume = pipe.flux * dt
			pipe.a.volume_change -= volume
			pipe.b.volume_change += volume

		for x in range(self.width):
			for column in self.columns[x]:
				height_change = column.volume_change / self.tile
				column.fluid = max(min(column.fluid - height_change, column.floor), column.ceiling)

	def fluid_polygons(self, surface_size: tuple[float, float], scroll: tuple[float, float]) -> list[tuple[list[tuple[float, float]], list[tuple[float, float]]]]:
		def linked(a: FluidColumn, b: FluidColumn) -> bool:
			return b.ceiling <= a.fluid <= b.floor and a.ceiling <= b.fluid <= a.floor

		polygons = []
		visited = set()

		start_x = max(0, int(scroll[0] / self.tile) - 1)
		end_x = min(self.width, int((scroll[0] + surface_size[0]) / self.tile) + 2)

		for x in range(start_x, end_x):
			for column in self.columns[x]:
				if column.empty or column in visited:
					continue

				if column.fluid * self.tile > scroll[1] + surface_size[1] or column.floor * self.tile < scroll[1]:
					continue

				sequence: list[tuple[int, FluidColumn]] = []
				current_column = column
				current_x = x

				while current_column:
					sequence.append((current_x, current_column))
					visited.add(current_column)

					next_column = None
					if current_x + 1 < end_x:
						for right_column in self.columns[current_x + 1]:
							if linked(current_column, right_column):
								next_column = right_column
								break

					current_column = next_column
					current_x += 1

				top_points = []
				bottom_points = []

				for i, (sequence_x, sequence_column) in enumerate(sequence):
					left = sequence_x * self.tile - scroll[0]
					center = (sequence_x + 0.5) * self.tile - scroll[0]
					right = (sequence_x + 1.0) * self.tile - scroll[0]

					fluid = sequence_column.fluid * self.tile - scroll[1]
					floor = sequence_column.floor * self.tile - scroll[1]

					if i == 0:
						top_points.append((left, fluid))

					top_points.append((center, fluid))
					bottom_points.append((left, floor))
					bottom_points.append((right, floor))

					if i == len(sequence) - 1:
						top_points.append((right, fluid))

				bottom_points.reverse()
				polygons.append((top_points, top_points + bottom_points))

		return polygons
