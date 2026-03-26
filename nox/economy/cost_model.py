import random

class CostModel:

    @staticmethod
    def estimate_intelligence_cost(task):

        base = 10
        complexity_cost = task.complexity * 5

        randomness = random.uniform(0, 3)

        return base + complexity_cost + randomness