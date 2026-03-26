class WorldManager:

    def __init__(self):
        self.worlds = {}

    def create_world(self, world_id):

        from .world import NOXWorld

        world = NOXWorld(world_id)
        self.worlds[world_id] = world

        return world

    def get_world(self, world_id):
        return self.worlds.get(world_id)