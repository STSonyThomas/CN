import threading
import time
 
# Create a new class called shared resource to simulate the shared nature of a resource for which a contest is happening
class SharedResource:
    def __init__(self):
        self.data=0
        self.reader_count=0
        self.mutex=threading.Lock()
        self.rw_lock =threading.Lock()

    def reader(self):
        with self.mutex:
            if self.reader_count==0:
                self.rw_lock.acquire()
            self.reader_count+=1
        print(f"Reader {threading.current_thread().name} is reading {self.data}")
        time.sleep(1)
        with self.mutex:
            self.reader_count-=1
            if self.reader_count==0:
                self.rw_lock.release()
    def writer(self):
        self.rw_lock.acquire()
        self.data+=1
        print(f"Writer {threading.current_thread().name} is writing {self.data}")
        time.sleep(2)
        self.rw_lock.release()


if __name__ =="__main__":
    resource = SharedResource()
    readers=[threading.Thread(target=resource.reader, name=f"Reader={i}") for i in range(5)]
    writers=[threading.Thread(target=resource.writer,name=f"Writer={i}")for i in range(2)]
    for thread in readers+writers:
        thread.start()
    for thread in readers + writers:
        thread.join()