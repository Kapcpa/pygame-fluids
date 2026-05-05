# A high-performance pure python fluid simulation for 2D games with a visual layer done with pygame



https://github.com/user-attachments/assets/554d6857-e8fd-42b1-bc3d-891ac8a68529



Please see example.py for an example on how to use the provided Water module.
Please see water.py for an example on how to create different types of fluids with the Fluid class.

Important functions and objects:

## water.Water:

`water.Water(width: int, height: int, tile: int)` - initializes the Water object, which takes the raw simulation from Fluid object and adds a visual and interaction layers on top of it

`water.Water.submerged(x: float, y: float)` - Returns True if the given world coordinate is underwater.

`water.Water.surface_level(x: float, y: float)` - Returns the surface level for a water column that includes the given x, y position (if such exists), None otherwise

`water.Water.near_surface(x: float, y: float, threshold: float)` - Checks if a point is close to the water surface. Threshold sets the minimum required distance to be considered as close.

`water.Water.add_force(x: float, y: float, strength: float)` - Applies downward or upward force to the fluid surface.

`water.Water.add_water_source(x: float, y: float, amount: float)` - Creates a constant inflow of water every frame.

`water.Water.clear_sources()` - Clears water sources

## fluid.Fluid:

`fluid.Fluid(width: int, height: int, tile: int)` - Initializes the Fluid object, which is responsible for simulation - generating water columns based on tile structure, calculating inflows and outflows, advancing the simulation.

`fluid.Fluid.set_wall(x, y, solid, update_fluid_structure)` - Updates the collision grid and rebuilds structures. The bool update_fluid_structure can be set to False to delay the update and should be used if you know you'll be adding many walls.
  
`fluid.Fluid.flip_wall(x: int y: int)` - Toggles a specific tile between solid/empty.

`fluid.Fluid.add_fluid(x: int, y: int, amount: float, dt: float)` - Adds fluid into the simulation at the given grid coordinates.

`fluid.Fluid.update_fluid_structure()` - Updates the columns based on current wall structure.

`fluid.Fluid.update(dt: float)` - advances the simulation.

`fluid.Fluid.fluid_polygons(surface_size: tuple[int, int], scroll: tuple[float, float])` - Returns raw vertex lists for rendering the fluid surface.
