"""
Daniel Sapojnikov - MODULE PART (PEER) 🐐
"""

# Cosmetic modules (Make it easier to handle strings)
import re
import ast
import time


# Important modules for the project.
import os
import pickle
import _pickle
import subprocess
import sqlite3 as sl
from socket import *
from pathlib import Path
from threading import Thread

# PEER object gets its GUI from an external file.
# API for communication with the CONNECTIONS SERVER.
try:
    import utils.local_servers.Api as Api
except ModuleNotFoundError:
    print("Error loading API, please consider looking into your files.")


# REGEX variables.
FILTER_REG = r'[^\w\n|.]'
IP_REG = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?=\s|\Z)'


def server_side_credentials():

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

# Utils
NAME = "Daniel"

# Own address
ADDRESS = list(server_side_credentials())

# Class server
CONNECTIONS_SERVER = Api.CONNECTIONS_SERVER


class Peer:

    SEGMENT_SIZE = 1024 * 1024
    BUFFER_SIZE = 1024 * 1024

    def __init__(self, name, controller, gui) -> None:

        self.gui = gui
        self.controller = controller
        self.controller.peer = self

        # configure multiple databases.
        self.name = name

        db_name = "peer.db"
        table_name = "peer_table"

        self.db = db_name
        self.table_name = table_name
        self.open_db()

        self.admin = ()
        self.files = dict()
        self.current_num_peers = 0
        self.online_peers = []

        # server side socket. (the socket who listens to requests and notifications from admin.)
        self.server_sock = socket(AF_INET, SOCK_STREAM)

        # client side socket (the socket who is connected to the admin.)
        self.client_sock = socket(AF_INET, SOCK_STREAM)
        self.management_connect()

        # BIND
        self.server_sock.bind(SERVER_ADDRESS)
        self.server_sock.listen(5)

        print(f"""
    Starting peer...
    SERVER SOCKET: {self.server_sock.getsockname()}
    CLIENT SOCKET: {self.client_sock.getsockname()}, PEER: {self.client_sock.getpeername()} 
        """)

        self.listen()

    def listen(self):

        while True:
            # establish a connection.
            other_sock, addr = self.server_sock.accept()
            Thread(target=self.handle_peer, daemon=True, args=(other_sock,)).start()

    def handle_peer(self, sock):

        final_file_transfer, meta_data, header_received = b"", b"", b""

        while True:
            # recv files.

            try:
                data = sock.recv(Peer.BUFFER_SIZE)

            except (ConnectionResetError, ConnectionRefusedError, Exception) as e:

                print(f"First Error: {e}")
                break

            if not data:
                break

            try:
                if data != b'':

                    # Check for file requests.
                    if type((request := pickle.loads(data))) is dict and request['notification'] == 'get_file':

                        print(f"{sock.getpeername()} REQUESTS: {request}")
                        self.forward_file_to_destination(request)

                    # got file_data from request!
                    elif type((request := pickle.loads(data))) is dict and request['notification'] == 'send_file':

                        print(f"GOT: {request} from {sock.getsockname()}")
                        self.assemble_file(request)

                    # HEADER transfer.
                    elif type((request := pickle.loads(data))) is tuple and request[0] == 'TRANSFER':
                        meta_data = request[1:]

                    else:
                        final_file_transfer += data

            except (_pickle.UnpicklingError, Exception) as e:

                print(f"Error: {e}")
                final_file_transfer += data

        if meta_data != b"" and final_file_transfer != b"":

            # Update tables.
            self.update_table(meta_data[0], meta_data[1], len(final_file_transfer), meta_data[2], final_file_transfer)

            # update the admin.
            self.update_admin_upon_receive(meta_data[0])

            if meta_data[3] == self.name:
                line = f'Server side got a part of: {meta_data[0]} / size: {len(final_file_transfer)}'
            else:
                line = f'Received a part of {meta_data[0]} / size: {len(final_file_transfer)} bytes / Uploader: {meta_data[3]}'

            self.controller.parse_data_to_update_list(line)

        sock.close()

    def assemble_file(self, document):

        print(f"{self.name} Assembling file: {document['file_name']}")

        data = b''
        flag = False
        file_name = document['file_name']

        try:
            with open(file_name, 'rb+') as shared_torrent_file:

                shared_torrent_file.seek(0, 0)
                data = shared_torrent_file.read()

            flag = True

        except Exception as e:

            print(f'ERROR! {e}')
            print(f"{document['file_name']} hasn't been created!")
            print(f"We are creating {document['file_name']}")

            with open(file_name, 'wb+') as shared_torrent_file:
                shared_torrent_file.write(document['raw_data'])

        finally:

            if flag:
                print(f"{document['file_name']} already created, writing part: {document['index']}")
                with open(file_name, 'wb+') as shared_torrent_file:

                    shared_torrent_file.seek(0, 0)
                    shared_torrent_file.write(data + document['raw_data'])

            # Update the bar.
            full_size = document['full_size']
            bytes_inc = int(len(document['raw_data']))
            file_name = document['file_name']

            Thread(target=self.gui.open_progress_bar, args=(file_name, bytes_inc, full_size)).start()

    def forward_file_to_destination(self, document):

        # fetch file from db.
        try:

            file_name = document['file_name']
            destination = document['destination']

            entry = sl.connect(self.db)
            cursor = entry.cursor()

            # Fetch needed data.
            query = f"""SELECT * FROM {self.table_name}"""
            cursor.execute(query)

            row = ()
            for file_row in cursor.fetchall():

                if file_row[0] == file_name:
                    row = (file_row[1], file_row[-2], file_row[-1])
                    break

            cursor.close()
            entry.close()

            # print("FILE TRANSFER DOCUMENT: ", file_transfer)
            TCP_transfer_sock = socket(AF_INET, SOCK_STREAM)
            TCP_transfer_sock.connect(destination)

            # construct payload.
            file_transfer = {
                'notification': 'send_file',
                'file_name': file_name,
                'index': row[0],
                'full_size': row[1],
                'raw_data': row[2]
            }

            # TRANSFER THE FILE!
            pickled_transfer = pickle.dumps(file_transfer)
            TCP_transfer_sock.send(pickled_transfer)
            print(f"Sent to {destination} TRANSFER of index {file_transfer['index']} "
                  f"FROM: {TCP_transfer_sock.getsockname()}")
            time.sleep(0.5)

        except Exception as e:
            raise e

    def download_file(self, file_name):

        """
        Downloads from all peers every slice of file in 'path'
        :param: file_name
        :return:
        """

        print(f"{self.server_sock} will now ask for: {file_name}")

        # Set online peers again!
        self.set_online_peers()

        if not self.current_num_peers >= 1:
            print("Low number of peers to perform this action.")
            return

        all_peers_documents = self.get_file_peers(file_name)
        sorted_documents = dict(sorted(all_peers_documents.items(), key=lambda meta_data: meta_data[1][1]))
        print(f"Any node who has: {file_name} is: \n{sorted_documents}")

        # ASKING EVERY PEER.
        for server_sock, peer_document in sorted_documents.items():

            TCP_request_sock = socket(AF_INET, SOCK_STREAM)
            try:

                TCP_request_sock.connect(server_sock)

                # ask the peer for the files' data.
                request_document = {
                    'notification': 'get_file',
                    'destination': SERVER_ADDRESS,
                    'file_name': file_name
                }
                pickled_request = pickle.dumps(request_document)
                TCP_request_sock.send(pickled_request)

                time.sleep(1)

            except (ConnectionResetError, ConnectionRefusedError, Exception) as e:

                print(f"Error: {e}")
                line = f'Download of {file_name} failed as one of the peers crashed :('
                self.controller.parse_data_to_update_list(line)
                break

    def get_file_peers(self, file_name):

        """
        Function that requests the admin for every peer that hold a slice of FILE_NAME.
        :type file_name: object
        :param file_name:
        :return:
        """

        document = {
            'notification': 'get peers',
            'file_name': file_name
        }
        request = pickle.dumps(document)

        # ask the admin for
        try:
            self.client_sock.send(request)
        except (ConnectionRefusedError, ConnectionResetError, Exception) as e:

            # Communicate with other peers.
            print('no admin')

        received_document = {}
        while True:

            data = self.client_sock.recv(Peer.BUFFER_SIZE)
            if not data:
                break

            if type(doc := pickle.loads(data)) is dict:
                received_document = doc
                break

        return received_document

    def upload_file(self, path: str) -> None:

        self.set_online_peers()
        print('new value to online peers: ', self.online_peers)

        if not self.current_num_peers >= 1:
            print("Low number of peers to perform this action.")
            return

        if not Path(path).exists():
            print(path, "Does not exist.")
            return

        file_name = os.path.basename(path)

        # the DOC dictionary stores for each PEER its part and index (for easier reassembly)
        doc = {peer: [] for peer in self.online_peers}

        sent_bytes = 0
        b_size = os.path.getsize(path)
        print(f'Size of {path} is: {b_size}')

        if b_size // self.current_num_peers <= Peer.SEGMENT_SIZE:

            # if the binary size of the file is small enough, every node will get the WHOLE file.
            chunk = b_size
            remainder = chunk % (chunk // self.current_num_peers)

            # Loop that builds the DOC if b_size is enough for the buffer.
            for i, peer in enumerate(self.online_peers):

                # last peer.
                if i == self.current_num_peers - 1:
                    doc[peer] = [chunk // self.current_num_peers + remainder, i]
                else:
                    doc[peer] = [chunk // self.current_num_peers, i]
        else:

            # print("Complex chunk calculation.")
            check_size, chunk = b_size, b_size // self.current_num_peers
            remainder = b_size % chunk

            for i, peer in enumerate(self.online_peers):

                # renew chunk.
                chunk = b_size // self.current_num_peers
                if check_size < Peer.SEGMENT_SIZE:
                    break
                if i == self.current_num_peers - 1:
                    chunk += remainder

                # check size.
                while chunk > Peer.BUFFER_SIZE:

                    diff_size = chunk - Peer.BUFFER_SIZE
                    doc[peer].append(Peer.BUFFER_SIZE)

                    if 0 < diff_size < Peer.BUFFER_SIZE:
                        doc[peer].append(diff_size)
                    chunk -= Peer.BUFFER_SIZE

                # add the index.
                doc[peer].append(i)
                check_size -= chunk

        with open(path, 'rb') as file:

            for i, peer in enumerate(self.online_peers):

                TCP_upload_socket = socket(AF_INET, SOCK_STREAM)
                try:
                    # Send and close.
                    TCP_upload_socket.connect(peer)

                except (ConnectionResetError, ConnectionRefusedError, Exception) as e:

                    line = f'Upload failed as one of the peers crashed :('
                    self.controller.parse_data_to_update_list(line)
                    return

                # create header
                header = pickle.dumps(('TRANSFER', file_name, i, b_size, self.name))
                TCP_upload_socket.send(header)

                # sleep one second (the difference between line 227 & the loop if very minor)
                time.sleep(1)

                # try to send, if there is an exception we retrieve the segment and parse it to another.
                for chunk in doc[peer][: -1]:
                    bin_file = file.read(chunk)

                    try:
                        # Send and close.
                        TCP_upload_socket.send(bin_file)
                        sent_bytes += chunk

                    except (ConnectionResetError, ConnectionRefusedError, Exception) as e:

                        line = f'Upload failed as one of the peers crashed during transition.'
                        self.controller.parse_data_to_update_list(line)
                        return

                    time.sleep(0.25)

                # close connection.
                TCP_upload_socket.close()

        print(f"We just sent to all the peers: {sent_bytes} bytes of {file_name}")

        line = f'You have uploaded {file_name}! / size: {b_size} bytes'
        self.controller.parse_data_to_update_list(line)

    def get_files(self):

        self.client_sock.send('GET FILES'.encode('utf-8'))

        message = ''
        while True:

            data = self.client_sock.recv(Peer.BUFFER_SIZE)
            if not data:
                break

            if type(doc := pickle.loads(data)) is dict and doc['notification'] == 'get_files':
                message = doc['files']
                break

        return message

    def update_admin_upon_receive(self, file_name):

        """
        Updates the admin on the current file download.
        :param: file_name
        :return:
        """
        try:
            entry = sl.connect(self.db)
            cursor = entry.cursor()

            # fetch all the data related to file_name.
            selection_query = f"""SELECT * FROM {self.table_name}"""
            cursor.execute(selection_query)

            final_notification, meta_data = b"", dict()
            for row in cursor.fetchall():

                if row[0] == file_name:
                    # pickle msg.
                    meta_data = {
                        'notification': 'update_file_db',
                        'name': self.name,
                        'meta_data': row[0: -1]
                    }
                    final_notification = pickle.dumps(meta_data)
                    break

            print(f"Sending to admin! \n{meta_data}")
            self.client_sock.send(final_notification)

        except (ConnectionResetError, ConnectionRefusedError, Exception) as e:

            print("No admin...")
            return

    def set_online_peers(self):
        try:

            print('Client socket peer: ', self.client_sock.getpeername())

            received_data = b""

            try:
                self.client_sock.send('GET PEERS'.encode('utf-8'))
            except Exception:

                line = f'Unable to get peers from admin, using current peers list'
                self.controller.parse_data_to_update_list(line)

            while True:

                data = self.client_sock.recv(Peer.BUFFER_SIZE)

                if not data:
                    break

                print("GETTING: ", data)
                received_data += data

                if bytes('CURRENT PEERS: ', 'utf-8') in received_data:
                    break

            print(received_data[15:])
            unpickled_data = pickle.loads(received_data[15:])
            print("Admin sent us the list: ", unpickled_data)

            # online peers.
            self.online_peers = [address for address in unpickled_data]
            self.current_num_peers = len(self.online_peers)

        except (ConnectionRefusedError, ConnectionResetError, Exception) as e:

            print("admin fell...")
            return

    def open_db(self):

        """
        Opens the database
        :return:
        """

        entry = sl.connect(self.db)
        cursor = entry.cursor()
        try:

            # Open a table named online-users.
            cursor.execute(f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
                file_name TEXT,
                slice_index INTEGER,
                slice_size INTEGER,
                exp_size INTEGER,
                data BLOB
                )""")

            # close all the resources.
            entry.commit()
            cursor.close()
            entry.close()

        except Exception as e:
            print(e)
            print("TABLE ALREADY EXISTS!")
        finally:
            return

    def update_table(self, file_name, slice_index, slice_size, exp_size, data):

        """
        Updates the database with that address.
        :param exp_size:
        :param file_name:
        :param slice_index:
        :param slice_size:
        :param data:
        :return:
        """

        entry = sl.connect(self.db)
        cursor = entry.cursor()

        # determine the values of the row and add them to the table.

        row = file_name, slice_index, slice_size, exp_size, data
        cursor.execute(f"""INSERT INTO {self.table_name} VALUES(?, ?, ?, ?, ?)""", row)

        entry.commit()
        entry.close()

    def management_connect(self) -> None:

        TCP_sock = socket(AF_INET, SOCK_STREAM)
        TCP_sock.connect(CONNECTIONS_SERVER)

        # Get the address.
        process_result = Api.Methods_API.get(TCP_sock, NAME)

        # Check if there was an Error.
        if not process_result['status']:
            raise Exception

        TCP_sock.close()
        self.admin = ast.literal_eval(process_result['addr'])
        print("Trying to connect to: ", self.admin)

        # connect to the admin.
        self.client_sock.connect(self.admin)

        # serialize the data.
        notification = f'ServerSock: {SERVER_ADDRESS}|{self.name}'.encode('utf-8')
        print(f"Sending: {notification} - SIZE: {len(notification)}")

        # send it to the ADMIN.
        self.client_sock.send(notification)

        while True:

            finish_handshake_data = self.client_sock.recv(Peer.BUFFER_SIZE)
            if not finish_handshake_data:
                break

            if type((doc := pickle.loads(finish_handshake_data))) is dict:

                if doc['notification'] == 'FIN':
                    print(f"Updating {self.admin} has been done.")
                    self.online_peers = doc['peers']
                    self.current_num_peers = len(self.online_peers)
                    break
