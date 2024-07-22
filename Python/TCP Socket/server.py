import socket

def readDetails():
    HOST=(input("Enter the host name eg. 127.0.0.1 for local host\t:"))
    PORT=int(input("Enter port to which need be connected eg;8000\t:"))
    return HOST,PORT

def socketProgramming(host,port):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.bind((host,port))
        s.listen(1)
        print(f"Listening on PORT;{port} for HOST;{host}")

        try:
            while True:
                c, addr = s.accept()
                print(f"Connection and addr {addr}")
                message = c.recv(1024).decode()
                print(message)
                c.send("Thank you for connecting".encode())
                c.close()
                break
        except socket.error as err:
            print(f"Error is {err}")
        finally:
            print("closed the socket at server side")
            s.close()

if __name__=="__main__":
    HOST,PORT=readDetails()
    socketProgramming(HOST,PORT)
