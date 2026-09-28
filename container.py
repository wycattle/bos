# pylint: disable=import-outside-toplevel,redefined-outer-name
'''Dependency Injection Container for Bos application'''

from typing import Dict, Any, Optional, Callable, TypeVar, Type
import threading
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt

T = TypeVar('T')

class Container:
    """Dependency Injection Container with singleton pattern and lazy loading"""
    
    _instance = None
    _lock = threading.RLock()   #Rlock ( reentrant lock) allows multiple modules to access the same thread
                                #a synchronization primitive used in multithreaded programming to prevent race conditions 
                                # and ensure thread safety when accessing shared resources
    
    def __new__(cls):   #__new__ is a built-in magic method responsible for creating and returning a new instance of a class. 
                        #While many developers mistake __init__ as the constructor, __init__ only initializes an object after
                        # it has already been allocated in memory. __new__ is the true constructor
                        
                        #cls = 'class' ----thread-safe implementation of the Double-Checked Locking Singleton Pattern
                        #Checks if a class-level variable named _instance has been created yet.
        if cls._instance is None:     
            with cls._lock:  #Uses a lock (which is also stored at the class level) to ensure multiple threads don't create two different objects at the exact same millisecond.
                if cls._instance is None:  #Checks if a class-level variable named _instance has been created yet.
                    cls._instance = super().__new__(cls)  #tells the parent class (super()) to allocate memory for a brand new object
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):     #self (the existing instance),

        if not getattr(self, '_initialized', False):
            print(f"Container starting up at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._dependency_graph = nx.DiGraph()
            self._singletons: Dict[str, Any] = {}
            self._factories: Dict[str, Callable] = {}
            self._transients: Dict[str, Callable] = {}
            self._creating: set = set() 
            self._creation_order = []
            self._lock = threading.RLock()
            self._initialized = True
            self._register_dependencies()
            print(f"Container initialization complete at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")            


    def _register_dependencies(self):
        """Register all dependencies with their creation functions  
            A singleton is a design pattern that ensures a class has only one instance
            throughout the entire application lifecycle. Once created, the same instance is reused every time you ask for it
            When someone asks for 'date_range' use the _create_date_range method to create it
            But only create it ONCE (singleton behavior)
            Lazy Creation - The actual DateRange instance is only created when someone first calls: container.get('date_range)"""     
        # Register core data dependencies
        self.register_singleton('milk_basics', self._create_milk_basics)
        self.register_singleton('date_range', self._create_date_range)
        
        # Status
        self.register_singleton('status_data',          self._create_status_data)
        self.register_singleton('wet_dry',              self._create_wet_dry)
        self.register_singleton('whiteboard_groups',    self._create_whiteboard_groups)
        self.register_singleton('model_groups_tenday',  self._create_model_groups)
        self.register_singleton('bos_state_orchestrator',self._create_bos_state_orchestrator)   
        
        # Insem
        self.register_singleton('insem_ultra_basics',   self._create_insem_ultra_basics)
        self.register_singleton('insem_ultra_data',     self._create_insem_ultra_data)
        self.register_singleton('check_last_stop',      self._create_check_last_stop)
        self.register_singleton('i_u_merge',            self._create_i_u_merge)
        self.register_singleton('ipiv_data',            self._create_ipiv)
        self.register_singleton('ipiv_pivot_table',     self._create_ipiv_pivot_table)
        self.register_singleton('next_ultra_check',     self._create_next_ultra_check)
        self.register_singleton('is_pregnant',          self._create_is_pregnant)
        
        # Feed
        self.register_singleton('feedcost_basics',      self._create_feedcost_basics)
        self.register_singleton('feedcost_data_loader', self._create_feedcost_data_loader)
        self.register_singleton('feedcost_data_processor', self._create_feedcost_data_processor)
        self.register_singleton('feedcost_by_group_by_day',    self._create_feedcost_by_group)
      

        # milk_functions
        self.register_singleton('milk_aggregates_basic', self._create_milk_aggregates_basic)
        self.register_singleton('milk_aggregates',       self._create_milk_aggregates)
        self.register_singleton('daily_milk_vs_fullday', self._create_daily_milk_vs_fullday)

        #plot functions
        self.register_singleton('plot_net_revenue_model', self._create_plot_net_revenue_model)
        self.register_singleton('run_lactation_plot',     self._create_run_lactation_plot)
        self.register_singleton('date_of_change',           self._create_date_of_change)
        
        #groups and tests
        self.register_singleton('whiteboard_groups',    self._create_whiteboard_groups)     
        self.register_singleton('model_groups',         self._create_model_groups)     
        self.register_singleton('compare_model_whiteboard_groups_last', self._create_compare_model_whiteboard_groups_last)     
     
        # Lactation
        self.register_singleton('lactation_basics',     self._create_lactation_basics)
        self.register_singleton('create_lactations',    self._create_lactations)
        self.register_singleton('this_lactation',       self._create_this_lactation)
        self.register_singleton('weekly_lactations',    self._create_weekly_lactations)
        self.register_singleton('lactations',           self._create_lactations)        
        self.register_singleton('lactation_plots',      self._create_lactation_plots)                                          
      

        # Finance
        self.register_singleton('finance_basics',       self._create_finance_basics)
        self.register_singleton('capex_basics',         self._create_capex_basics)         
        self.register_singleton('capex_projects',       self._create_capex_projects)
        self.register_singleton('net_income',           self._create_net_income)        
        self.register_singleton('milk_income',          self._create_milk_income)
        self.register_singleton('depreciation',         self._create_depreciation)        
        self.register_singleton('net_revenue',          self._create_net_revenue)
        self.register_singleton('net_revenue_by_cow',   self._create_net_revenue_by_cow)

        # pipeline dependencies
        self.register_singleton('format_for_neon',      self._create_format_for_neon)
        self.register_singleton('daily_modal_data',     self._create_daily_modal_data)    
        # self.register_singleton('occasional_modal_stage1', self._create_occasional_modal_stage1)
        # self.register_singleton('occasional_modal_stage2', self._create_occasional_modal_stage2)
        # self.register_singleton('modal_orchestrator',   self._create_modal_orchestrator)

        

    def register_singleton(self, name: str, factory: Callable[[], Any]):
        """Register a singleton dependency"""
        self._factories[name] = factory
    
    def register_transient(self, name: str, factory: Callable[[], Any]):
        """Register a transient dependency (new instance each time)"""
        self._transients[name] = factory
            
    def get(self, name: str) -> Any:
        """Get a dependency by name, ensuring it is fully initialized (including load_and_process)."""
        with self._lock:
            if not hasattr(self, '_creation_order'):
                self._creation_order = []

            # Record edge every time - regardless of cache hit - so the graph
            # reflects every caller->dependency relationship, not just first discovery
            if self._creation_order:
                self._dependency_graph.add_edge(self._creation_order[-1], name)

            # Return existing singleton if already created
            if name in self._singletons:
                return self._singletons[name]

            # Check if it's a registered singleton factory
            if name in self._factories:
                if not hasattr(self, '_creating'):
                    self._creating = set()

                if name in self._creating:
                    print("CIRCULAR DEPENDENCY DETECTED!")
                    raise RuntimeError(f"Circular dependency: {' → '.join(self._creation_order)} → {name}")

                self._creating.add(name)
                self._creation_order.append(name)

                try:
                    instance = self._factories[name]()
                    load_proc = getattr(instance, "load_and_process", None) or getattr(instance, "load", None)
                    if callable(load_proc):
                        if not hasattr(instance, "_load_and_process_called"):
                            load_proc()
                            setattr(instance, "_load_and_process_called", True)
                    self._singletons[name] = instance
                    return instance
                finally:
                    self._creating.remove(name)
                    self._creation_order.remove(name)
                    print(f"Finished creating: {name}")

            # Check if it's a transient
            if name in self._transients:
                print(f"Creating transient: {name}")
                instance = self._transients[name]()
                load_proc = getattr(instance, "load_and_process", None)
                if callable(load_proc):
                    if not hasattr(instance, "_load_and_process_called"):
                        load_proc()
                        setattr(instance, "_load_and_process_called", True)
                return instance

            raise ValueError(f"Dependency '{name}' not registered")
        
    def get_typed(self, dependency_type: Type[T], name: Optional[str] = None) -> T:
        """Get a typed dependency"""
        key = name or dependency_type.__name__.lower()
        return self.get(key)

    
    def record_table_read(self, table_name: str):
        """Log a raw table read against whichever dependency is currently
        being constructed. Called by the SQLAlchemy engine listener in
        neon_connect.py — not by application code directly."""
        with self._lock:
            if self._creation_order:
                node = f"table:{table_name}"
                self._dependency_graph.add_edge(self._creation_order[-1], node)
                
    
    def reset(self):
        """Reset all singletons (useful for testing)"""
        with self._lock:
            self._singletons.clear()
    
    def list_dependencies(self) -> Dict[str, str]:
        """List all registered dependencies"""

        #The ** "spreads" the key-value pairs from one dictionary into another dictionary.
        #This merges two dictionaries—one mapping singleton names to 'singleton', the other mapping transient names to 'transient'—into a single dictionary. 
        # If a name appears in both, the last one wins.
        return {
            **{name: 'singleton' for name in self._factories},   
            **{name: 'transient' for name in self._transients}
        }
    
        # Visualization of dependencies
    def show_dependency_graph(self):
        from pyvis.network import Network

        net = Network(height='800px', width='100%', directed=True, notebook=False)
        net.from_nx(self._dependency_graph)
        net.show_buttons(filter_=['physics'])  # lets you tune layout live in-browser
        net.save_graph("dependency_graph.html")
        print("Open dependency_graph.html by clicking the Go Live button on bottom activity bar")



    
    # general functions 
    def _create_milk_basics(self):
        from milk_basics import MilkBasics
        return MilkBasics()

    def _create_date_range(self):
        from date_range import DateRange
        return DateRange()
    

    # Status functions
    def _create_status_data(self):
        from status_functions.status_data import status_data
        return status_data()
    
    def _create_wet_dry(self):
        from status_functions.wet_dry import WetDry
        return WetDry()
    
    def _create_bos_state_orchestrator(self):
        from status_functions.bos_state_orchestrator import BosStateOrchestrator
        return BosStateOrchestrator()
    
    
    
    # Insem functions
    def _create_insem_ultra_basics(self):
        from insem_functions.insem_ultra_basics import InsemUltraBasics
        return InsemUltraBasics()
            
    def _create_insem_ultra_data(self):
        from insem_functions.insem_ultra_data import InsemUltraData
        return InsemUltraData()
        
    def _create_check_last_stop(self):
        from insem_functions.check_laststop import CheckLastStop
        return CheckLastStop()

    def _create_i_u_merge(self):
        from insem_functions.I_U_merge import I_U_merge
        return I_U_merge()
    
    def _create_ipiv(self):
        from insem_functions.ipiv_data import IpivData
        return IpivData()
    
    def _create_ipiv_pivot_table(self):
        from insem_functions.ipiv_pivot_table import IpivPivotTable
        return IpivPivotTable()
    
    def _create_next_ultra_check(self):
        from insem_functions.next_ultra_check import NextUltraCheck
        return NextUltraCheck()
    
    def _create_is_pregnant(self):
        from insem_functions.is_pregnant import IsPregnant
        return IsPregnant()
    



    # Feed functions 
    def _create_feedcost_basics(self):
        from feed_functions.feedcost_basics import FeedcostBasics
        return FeedcostBasics()

    def _create_feedcost_data_loader(self):
        from feed_functions.feedcost_data_loader import FeedCostDataLoader
        return FeedCostDataLoader()
    
    def _create_feedcost_data_processor(self):
        from feed_functions.feedcost_data_loader import FeedCostDataProcessor
        loader = self.get("feedcost_data_loader") 
        return FeedCostDataProcessor(loader)
    
    def _create_feedcost_by_group(self):
        from feed_functions.feedcost_by_group_by_day import FeedCostByGroupByDay
        return FeedCostByGroupByDay()
    
    

    # Milk functions
    def _create_milk_aggregates_basic(self):
        from milk_functions.milk_aggregates_basic import MilkAggregatesBasic
        return MilkAggregatesBasic()

    def _create_milk_aggregates(self):
        from milk_functions.milk_aggregates import MilkAggregates
        return MilkAggregates()
    
    def _create_daily_milk_vs_fullday(self):
        from milk_functions.daily_milk_vs_fullday import DailyMilkVsFullday
        return DailyMilkVsFullday()
    
    
    # plot functions
    def _create_plot_net_revenue_model(self):
        from plot_functions.plot_net_revenue_model import PlotNetRevenueModel
        return PlotNetRevenueModel()
    
    def _create_run_lactation_plot(self):
        from plot_functions.Run_lactation_plot import RunLactationPlot
        return RunLactationPlot()
    
    def _create_date_of_change(self):
        from plot_functions.date_of_change import DateOfChange
        return DateOfChange()



    # Groups and tests  
    def _create_model_groups(self):
        from groups_and_tests.model_groups import ModelGroups
        return ModelGroups()
        
    def _create_whiteboard_groups(self):
        from groups_and_tests.whiteboard_groups import WhiteboardGroups
        wg = WhiteboardGroups()
        return wg
    
    def _create_compare_model_whiteboard_groups_last(self):
        from groups_and_tests.compare_model_whiteboard_groups_last import CompareModelWhiteboardGroups_Last
        return CompareModelWhiteboardGroups_Last()


    # Lactation functions 
    def _create_lactation_basics(self):
        from milk_functions.lactation.lactation_basics import LactationBasics
        return LactationBasics()
    
    def _create_this_lactation(self):
        from milk_functions.lactation.this_lactation import ThisLactation
        return ThisLactation()
    
    def _create_lactations(self):
        from milk_functions.lactation.lactations import Lactations
        return Lactations()
    
    def _create_weekly_lactations(self):
        from milk_functions.lactation.weekly_lactations import WeeklyLactations
        return WeeklyLactations()
    
    
    
    # Lactation measurements

    def _create_lactation_plots(self):
        from plot_functions.lactation_plots import LactationPlots
        return LactationPlots()        
    


    # Pipeline
    def _create_format_for_neon(self):
        from pipeline.neon.format_for_neon import FormatForNeon
        return FormatForNeon()  
    
    def _create_daily_modal_data(self):
        from pipeline.modal.daily_modal import DailyModal
        return DailyModal()
    


    # Finance functions 
    def _create_finance_basics(self):
        from finance_functions.finance_basics import FinanceBasics
        return FinanceBasics()
    
    def _create_capex_basics(self):
        from finance_functions.capex.capex_basics import CapexBasics
        return CapexBasics()  
     
    def _create_capex_projects(self):
        from finance_functions.capex.capex_projects import CapexProjects
        return CapexProjects()

    def _create_net_income(self):
        from finance_functions.PL.net_income import NetIncome
        return NetIncome()       

    def _create_milk_income(self):
        from finance_functions.milk_income import MilkIncome
        return MilkIncome()
        
    def _create_depreciation(self):
        from finance_functions.PL.depreciation import DepreciationCalc
        return DepreciationCalc()
    
    def _create_net_revenue(self):
        from finance_functions.PL.net_revenue import NetRevenue
        return NetRevenue()
        
    def _create_net_revenue_by_cow(self):
        from finance_functions.PL.net_revenue_by_cow import NetRevenueByCow
        return NetRevenueByCow()



# Global container instance
container = Container()

# Convenience functions
def get_dependency(name: str) -> Any:
    """Get a dependency from the global container"""
    return container.get(name)

def get_typed_dependency(dependency_type: Type[T], name: Optional[str] = None) -> T:
    """Get a typed dependency from the global container"""
    return container.get_typed(dependency_type, name)

def reset_container():
    """Reset the global container (useful for testing)"""
    container.reset()

    
#Yes, your if __name__ == "__main__": guard is correct.
#It ensures that the code inside only runs when you execute container.py directly, 
# not when it is imported as a module.
if __name__ == "__main__":
    pass
