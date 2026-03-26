class NOXWorld:

    def __init__(self, world_id):

        self.world_id = world_id
        self.communities = {}
        self.state = {}
        self.history = []

    def register_community(self, community):

        self.communities[community.name] = community

    def get_community(self, name):
        return self.communities.get(name)

    def log_event(self, event):

        self.history.append(event)