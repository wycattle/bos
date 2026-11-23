'''check_laststop.py'''
import inspect
from container import get_dependency


class CheckLastStop:
    def __init__(self):
        
        print(f"CheckLastStop instantiated by: {inspect.stack()[1].filename}")
        # print(f"🔍 {self.__class__.__module__}: Current stack:")
        # for i, frame in enumerate(inspect.stack()[:5]):
        #     print(f"   {i}: {frame.filename}:{frame.lineno} in {frame.function}")        

        self.MB = None
        self.DR = None
        self.data = None
        self.SD = None
        self.IUB = None
        self.IUD = None
        self.allx = None
        self.status_col = None
        self.last_stop = None
        self.last_start = None
        self.listx = None

    def load(self):
        self.MB = get_dependency('milk_basics')
        self.DR = get_dependency('date_range')
        self.data = self.MB.data
        self.SD = get_dependency('StatusData')
        self.IUB = get_dependency('insem_ultra_basics')
        self.IUD = get_dependency('insem_ultra_data')
        self.process()
        
    def process(self):
        self.allx = self.IUD.allx.iloc[:, :5].copy()
        self.status_col = self.SD.status_col
        self.last_stop = self.IUB.last_stop
        self.last_start = self.IUB.last_calf

        self.last_stop.index = self.last_stop.index - 1
        self.last_start.index = self.IUB.last_calf.index - 1

        self.listx = self.create_list()
        print("✅ CheckLastStop: Complete!")



        # this is to identify missing last_stop dates. 
        # cows that are alive and milking but the laststop date/calf_num is missing
        
    def create_list(self):
        self.listx = []
                # status_col is a DataFrame with wy_id index and one dynamic column → extract as Series
        status = self.status_col.iloc[:, 0]  # Series: index=wy_id, values=status
        
        lstop  = self.last_stop["last_stop_date"]
        lstart = self.last_start["last_calf_bdate"]
        for i in status.index.tolist():
            if i in self.last_stop.index and i in self.last_start.index:
                a = lstop[i]
                b = lstart[i]
                c = (status[i] == 'M')
                # d = (self.status_col != 'D')
              
                condition1 = a < b  # there is no birth after the last stop
                condition2 = c  # last status is 'M' 


                if condition1 and condition2:
                    self.listx.append(i)
            else:
                print(f"Index {i} not found in last_stop or last_start")
                
        if not self.listx:
            print('no laststop errors, self.listx is empty')
   

        return self.listx

if __name__ == "__main__":
    obj=CheckLastStop()
    obj.load()  