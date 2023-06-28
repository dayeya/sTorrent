"""
Daniel Sapojnikov - MODULE PART (ADMIN) 🐐, 🏆
"""

# Cosmetic modules (Make it easier to handle strings)
import re
import ast
from datetime import datetime

# Important modules for handling data.
import pickle  # - serialization
import subprocess  # - Processes
import sqlite3 as sl  # - Database management.
from socket import *  # - Networking and communication.
from threading import Thread  # Threading

# GUI of admin.
from utils.gui.GUI_connector import Admin_GUI

try:
    import utils.local_servers.Api as Api
except ModuleNotFoundError:
    print("Error loading API, please consider looking into your files.")

# REGEX variables.
FILTER_REG = r'[^\w\n|.]'
IP_REG = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?=\s|\Z)'

# For easier usage.
global client_socks
client_socks = dict([])


def admin_side_credentials():
    """
    RETURNS: the credentials of the server -> (IP, PORT)
    1. uses subprocess to fetch the ip + string manipulation.
    2. uses the following 'port' code in order to find the first OPEN port on the device - (SERVER).
    :returns: tuple
    """

    data = subprocess.check_output('ipconfig').decode('utf-8')
    data = re.sub(FILTER_REG, '', data)

    k = data.index("IPv4Address") + 1  # the index of the ip address.
    ip = re.search(IP_REG, data[k: data.index('\n', k)])
    ip = ip.group(0) if ip is not None else None

    # PORT
    scan_socket = socket(AF_INET, SOCK_STREAM)
    scan_socket.bind(("", 0))
    scan_socket.listen(1)

    port = scan_socket.getsockname()[1]
    scan_socket.close()

    return ip, port


# Important utils.
NAME = 'Daniel'

# Addresses.
ADDRESS = admin_side_credentials()

# Class server.
CONNECTIONS_SERVER = Api.CONNECTIONS_SERVER


class Admin:
    BUFSIZE = 8 * 1024

    def __init__(self, gui):

        self.gui = gui

        # Open server socket & update the CONNECTIONS server database.
        self.peers = []
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.update_connections_server()

        # Start listening.
        self.peers, self.files = 'peers.db', 'files.db'
        self.open_databases()

        self.sock.bind(ADDRESS)
        self.sock.listen(5)

        Thread(target=self.run_admin, daemon=True).start()

        self.gui.window.mainloop()

    def run_admin(self):

        print(f"Admin is up at: {ADDRESS}")

        while True:
            client, addr = self.sock.accept()

            # Create a thread to handle PEER.
            service = Thread(target=self.handle_client, daemon=True, args=(client, addr))
            service.start()

    def handle_client(self, sock: socket, addr: tuple):

        """
        :param addr:
        :type sock: object
        """

        print(f'Admin Handling {addr} for simple request.')

        while True:

            try:

                # Loop to get all the data (considering the buffer size)
                received_data = sock.recv(Admin.BUFSIZE)
                if not received_data:
                    break

                # :)
                data = received_data

                # check establishment of connection.
                if bytes('ServerSock: ', 'utf-8') in data:

                    data = data[12:].decode('utf-8').split('|')
                    name = data[1]
                    date = datetime.today().strftime('%H:%M:%S')
                    server_sock = ast.literal_eval(data[0].strip())

                    # Update database & GUI table.
                    client_socks.update({name: sock.getpeername()})
                    self.update_peers_table(name, server_sock, date)

                    doc = {
                        'action': 'insert',
                        'status': 'Online',
                        'name': name,
                        'parts': ''
                    }
                    self.gui.update_tree(doc)

                    entry = sl.connect(self.peers)
                    cursor = entry.cursor()

                    selection_query = """SELECT ip, port FROM online_users"""
                    cursor.execute(selection_query)
                    server_side_addresses = cursor.fetchall()

                    doc = {
                        'notification': 'FIN',
                        'peers': server_side_addresses
                    }

                    pickled_doc = pickle.dumps(doc)
                    sock.send(pickled_doc)

                elif data == bytes('GET PEERS', 'utf-8'):
                    self.send_online_peers(sock)

                elif data == bytes('GET FILES', 'utf-8'):
                    self.fetch_all_files(sock, addr)

                elif type((doc := pickle.loads(data))) is dict:

                    # Determine the notification.
                    notification = doc['notification']

                    if notification == 'update_file_db':
                        self.update_files_table(doc)

                        doc = {
                            'action': 'update',
                            'status': 'Online',
                            'name': doc['name'],
                            'parts': doc['meta_data'][0]
                        }

                        self.gui.update_tree(doc)

                    elif notification == 'get peers':
                        self.send_specific_peers(sock, doc)

            except (ConnectionRefusedError, ConnectionResetError, Exception) as e:

                # DELETE HERE!
                name = self.get_name(sock.getpeername())
                del client_socks[name]

                # Delete all needed references.
                self.delete_peer(name)
                self.gui.delete_peer(name)
                self.delete_peer_from_files(name)

                print(f"{e} has occurred, closing connection.")

                sock.close()
                break

        # Close socket.
        sock.close()

    def fetch_all_files(self, sock, addr):

        """
        Sends all the files in database to sock.
        :param sock:
        :param addr:
        :return:
        """

        print('For: ', addr)

        entry = sl.connect(self.files)
        cursor = entry.cursor()

        query = f"""SELECT * FROM files"""
        cursor.execute(query)

        # all data.
        files = cursor.fetchall()

        msg = {
            'notification': 'get_files',
            'files': list(map(lambda file: file[1], files))
        }
        print("SENDING TO UPDATE LIST!", msg)
        sock.send(pickle.dumps(msg))

    def send_specific_peers(self, sock, document):

        # requested file_name.
        requested_file = document['file_name']

        # get all data.
        entry = sl.connect(self.files)
        cursor = entry.cursor()

        # Execute the query.
        selection_query = f"""SELECT * FROM files"""
        cursor.execute(selection_query)

        # shared_file - (user_name, file_name, index, size_of_slice)
        relevant_peers = list(filter(lambda row: row[1] == requested_file, cursor.fetchall()))
        relevant_peers = {row[0]: row[1:] for row in relevant_peers}

        # close db variables.
        cursor.close()
        entry.close()

        # get all data.
        entry = sl.connect(self.peers)
        cursor = entry.cursor()

        # Execute the query.
        selection_query = f"""SELECT * FROM online_users"""
        cursor.execute(selection_query)

        # extend payload.
        final_document = dict()
        relevant_peer_names = relevant_peers.keys()
        for peer in cursor.fetchall():

            if peer[0] in relevant_peer_names:

                slot = {(peer[1:-1]): relevant_peers[peer[0]]}
                final_document.update(slot)

        # close connections.
        cursor.close()
        entry.close()

        pickled_document = pickle.dumps(final_document)
        sock.send(pickled_document)

    def send_online_peers(self, client_sock):

        """
        Sends the current online peers to all peers across the network every 3 seconds.
        :return:
        """
        try:
            print(f"FOR: {client_sock.getpeername()}")

            entry = sl.connect(self.peers)
            cursor = entry.cursor()

            selection_query = """SELECT ip, port FROM online_users"""
            cursor.execute(selection_query)
            server_side_addresses = cursor.fetchall()

            if len(server_side_addresses) >= 1:
                # create pickled data.
                pickled_peers_object = bytes("CURRENT PEERS: ", 'utf-8') + pickle.dumps(server_side_addresses)

                print(f"Sending to: {client_sock}\n{pickled_peers_object}")
                client_sock.send(pickled_peers_object)

        except Exception as e:
            raise e

    @staticmethod
    def get_name(del_sock):

        global client_socks

        return [key for key, value in client_socks.items() if value == del_sock][0]

    @staticmethod
    def update_connections_server() -> None:

        try:
            TCP_sock = socket(AF_INET, SOCK_STREAM)
            TCP_sock.connect(CONNECTIONS_SERVER)
            print(f"TCP socket created - {TCP_sock.getsockname()} for address forwarding")

            process_result = Api.Methods_API.set(TCP_sock, NAME, ADDRESS)
            if not process_result:
                raise Exception

            # Finis h handshake
            while True:
                data = TCP_sock.recv(Admin.BUFSIZE).decode('utf-8')
                if data == 'Fin':
                    TCP_sock.close()
                    print("Connections server has updated the address - booting up the server...")
                    break

        except (ConnectionRefusedError, ConnectionResetError, Exception) as e:
            print("Error occurred, maybe main server is not online.")
            raise e

    def open_databases(self):

        """
        Opens the database
        :return:
        """

        try:

            entry = sl.connect(self.peers)
            cursor = entry.cursor()

            # Open a table named online-users.
            cursor.execute("""CREATE TABLE online_users (
                NAME TEXT, 
                ip TEXT,
                port INTEGER,
                connection TEXT
                )""")

            # close all the resources.
            entry.commit()
            cursor.close()
            entry.close()

            entry = sl.connect(self.files)
            cursor = entry.cursor()

            cursor.execute("""CREATE TABLE files (
                NAME TEXT,
                FILE_NAME TEXT,
                INDEX_OF_SHARE INTEGER,
                SIZE_OF_SLICE INTEGER
                )""")

            # close all the resources.
            entry.commit()
            cursor.close()
            entry.close()

        except Exception as e:

            raise e

        finally:
            return

    def update_files_table(self, document_to_update):

        """
        Updates the admins file database.
        :param document_to_update:
        :return:
        """

        entry = sl.connect(self.files)
        cursor = entry.cursor()

        # DATA inserted to the database.
        user = document_to_update['name']
        meta_data = document_to_update['meta_data']
        inserted_data = user, meta_data[0], meta_data[1], meta_data[2]

        query = f'''INSERT INTO files VALUES(?, ?, ?, ?)'''
        cursor.execute(query, inserted_data)

        entry.commit()
        cursor.close()
        entry.close()

    def update_peers_table(self, name, addr, date):

        """
        Updates the database with that address.
        :param name:
        :param addr:
        :param date:
        :return:
        """

        entry = sl.connect(self.peers)
        cursor = entry.cursor()

        # determine the values of the row and add them to the table.
        ip, port = addr
        inserted_data = (name, ip, port, date)

        selection_query = """INSERT INTO online_users VALUES(?, ?, ?, ?)"""
        cursor.execute(selection_query, inserted_data)

        entry.commit()
        cursor.close()
        entry.close()

    def delete_peer(self, name):

        """
        Deletes the database with that name.
        :param name:
        :return:
        """

        entry = sl.connect(self.peers)
        cursor = entry.cursor()

        selection_query = """DELETE from online_users where NAME = ?"""
        cursor.execute(selection_query, (name, ))

        entry.commit()
        cursor.close()
        entry.close()

    def delete_peer_from_files(self, name):

        """
        Deletes the database with that name.
        :param name:
        :return:
        """

        entry = sl.connect(self.files)
        cursor = entry.cursor()

        selection_query = """DELETE from files where NAME = ?"""
        cursor.execute(selection_query, (name, ))

        entry.commit()
        cursor.close()
        entry.close()


if __name__ == "__main__":
    gui = Admin_GUI()
    Admin = Admin(gui)
