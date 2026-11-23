'''
status_functions.bos_state_orchestrator
'''

import inspect
from container import get_dependency, container

class BosStateOrchestrator:
    """
    Single source of truth for facts every downstream module needs:
    alive/dead/pregnant status, canonical wy_id list, as-of date.
    Consumed by: WetDry, ModelGroups, NetRevenue, PlotNetRevenueModel.
    """
    def __init__(self):
        
        print(f"BosStateOrchestrator instantiated by: {inspect.stack()[1].filename}")

        self.SD     = None
        self.MB     = None
        self.IUD    = None

    def load(self):
        self.SD  = get_dependency('StatusData')
        self.MB  = get_dependency('milk_basics')
        self.IP = get_dependency('is_pregnant')
        self.process()

    def process(self):
        pass
            
if __name__=='__main__':
    obj = BosStateOrchestrator()
    obj.load()
    container.show_dependency_graph()
            