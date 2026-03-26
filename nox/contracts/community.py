class BaseCommunity:

    name = "base_community"
    community_type = "directive"

    def process(self, task):
        raise NotImplementedError