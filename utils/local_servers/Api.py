from socket import *

# API FOR TORRENT.

'''
    $ GUIDE FOR THE API $
    
    Installation:
    1. Download Api.py and cred.py
    2. import Api, cred to ADMIN and CLIENT files. (any .py)
    3. To use the methods you may write: Api.Methods_API.<Method_Name>
    
'''

CONNECTIONS_SERVER = ('10.9.9.189', 60000)


class Methods_API:

    # no fields.
    @staticmethod
    def set(sock: socket, server: str, address: tuple) -> bool:
 
        """ $ SET $ - USED BY ADMIN (Management Server)
        static function, sends the message to the connections' server.
        :Purpose: to update the connections servers database with the credentials of the server.

        Parameters:
        server: the servers NAME.
        sock: the SOCKET the servers uses.
        address: the IP & PORT of the connection (Management_server) itself.
        
        OUTPUT:
        Boolean - True / False (Based of the outcome of the process)
        """

        ret = False
        try:
            sock.send(f'POST: {server}-{address}'.encode('utf-8'))
            ret = True

        except Exception as e:
            print(f"Error occurred: {e}")
            ret = False
        finally:
            return ret

    @staticmethod
    def get(sock: socket, server: str) -> dict:

        """ $ GET $ USED BY CLIENT (PEER)
        static function, sends the message to the connections' server.
        :Purpose: Give the PEER making this request, get the desired IP, PORT of the SERVER.

        Parameters:
        server: the servers NAME.
        sock: the SOCKET the servers uses.
        
        OUTPUT:
        Dictionary:
        'status': Boolean
        'Addr': ip, port
        """

        payload = dict()
        try:
            sock.send(f'GET: {server}'.encode('utf-8'))

            while True:

                data = sock.recv(1024).decode('utf-8')
                if not data:
                    return {'status': False}

                # fetch address
                address = data[len(server) + 4: len(data)].strip()
                payload = {
                    'status': True,
                    'addr': address
                }
                return payload

        except Exception as e:
            payload = {
                'status': False
            }

            # log the error 
            print(f"Error occurred: {e}")
        finally:
            return payload
