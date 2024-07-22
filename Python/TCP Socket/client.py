import socket

def createSocket(HOST,PORT):
    c=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    c.connect((HOST,PORT))
    return c
def collectDetails():
    HOST=input("Enter host name eg.127.0.0.1")
    PORT=int(input("Enter port name;8000"))
    return HOST,PORT
if __name__=="__main__":
    HOST,PORT=collectDetails()
    c= createSocket(HOST,PORT)
    c.send("This is client speaking".encode())
    data=c.recv(1024).decode()
    print(data)