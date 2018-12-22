# WS client example

import os
import json
import base64
import asyncio
import websockets

from datetime import datetime, timedelta

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def encryptMsg(response, public_key):
    message = str.encode(response)

    symmetric_key = os.urandom(32)
    symmetric_iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(symmetric_key), modes.OFB(symmetric_iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(message) + encryptor.finalize()


    key_cyphered = public_key.encrypt(
        symmetric_key,
        padding.PKCS1v15()
    )

    iv_cyphered = public_key.encrypt(
        symmetric_iv,
        padding.PKCS1v15()
    )

    out= key_cyphered+ b"PROJ_SIO_2018"+ iv_cyphered+ b"PROJ_SIO_2018"+ ct

    return out


def decryptMsg(request, private_key):
    requestList = request.split(b"PROJ_SIO_2018")

    symmetric_key = private_key.decrypt(
        requestList[0],
        padding.PKCS1v15()
    )

    symmetric_iv = private_key.decrypt(
        requestList[1],
        padding.PKCS1v15()
    )

    cipher = Cipher(algorithms.AES(symmetric_key), modes.OFB(symmetric_iv), backend=default_backend())
    decryptor = cipher.decryptor()
    message = decryptor.update(requestList[2]) + decryptor.finalize()

    jsonData = message.decode("utf-8")

    return symmetric_key, symmetric_iv, jsonData




async def interface():
    async with websockets.connect('ws://localhost:8765') as websocket1: # sioManager
        async with websockets.connect('ws://localhost:7654') as websocket2: # sioRepository
            with open("repository_public_key.pem", "rb") as repository_public_key_file:
                with open("manager_public_key.pem", "rb") as manager_public_key_file:
                    with open("client_public_key.pem", "rb") as client_public_key_file:
                        with open("client_private_key.pem", "rb") as client_private_key_file:
                            # Security Keys
                            manager_public_key = serialization.load_pem_public_key(manager_public_key_file.read(), backend=default_backend())
                            repository_public_key = serialization.load_pem_public_key(repository_public_key_file.read(), backend=default_backend())
                            client_public_key = serialization.load_pem_public_key(client_public_key_file.read(), backend=default_backend())
                            client_private_key = serialization.load_pem_private_key(client_private_key_file.read(), password=b"SIO_85048_85122", backend=default_backend())

                            # User Interface Menu
                            act = input("0-Leave\n1-Create Auction\n2-Close Auction\n3-List Auctions\n4-List Bids of Auction\n5-List Bids by Client\n6-Check Outcome\n7-Make Bid\nAction: ")
                            while act!="0":
                                if act!="1" and act!="2":
                                    message={"action":act}
                                    if act=="4" or act=="6":
                                        message["auction"]={"serialNum":input("Serial Number: ")}
                                    if act=="5":
                                        message["user"]=input("User: ")
                                    if act=="7":
                                        # Send encrypted message
                                        message["key"]=client_public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
                                        out = encryptMsg(json.dumps(message), repository_public_key)
                                        await websocket2.send(out)
                                        # Receive and decrypt response message
                                        response = await websocket2.recv()
                                        symmetric_key, symmetric_iv, data = decryptMsg(response, client_private_key)
                                        data = json.loads(data)
                                        # Solve Crypto Puzzle
                                        message["bid"]={"auction": input("Auction: "),"user": input("User: "),"amount":float(input("Amount: ")), "time":str(datetime.now())}
                                        puzzle = base64.b64decode(data['cryptopuzzle'])
                                        print("To solve this puzzle, your checksum must beggin with: " + base64.b64encode(puzzle).decode("utf-8"))
                                        proposals = set([])
                                        while True:
                                            random_bytes = os.urandom(16)
                                            message["bid"]["cryptoanswer"] = base64.b64encode(random_bytes).decode("utf-8")
                                            serialized_message = str.encode(json.dumps(message["bid"], sort_keys=True))
                                            concat = serialized_message + random_bytes
                                            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
                                            digest.update(concat)
                                            checksum = digest.finalize()
                                            checksum = checksum[0:len(puzzle)]
                                            if puzzle==checksum:
                                                proposals.add((checksum,random_bytes))
                                                break
                                            else:
                                                if len(proposals)<4:
                                                    proposals.add((checksum,random_bytes))
                                        for p in proposals:
                                            answer = input("Puzzle - " + base64.b64encode(puzzle).decode("utf-8") + " | Checksum - " + base64.b64encode(p[0]).decode("utf-8") + "\nDoes it solve the puzzle? (y/n): ")
                                            if answer=="y" or answer =="Y":
                                                message["bid"]["cryptoanswer"] = base64.b64encode(p[1]).decode("utf-8")
                                                break
                                    
                                    # Send encrypted message
                                    message["key"]=client_public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
                                    out = encryptMsg(json.dumps(message), repository_public_key)
                                    await websocket2.send(out)

                                    # Receive and decrypt response message
                                    response = await websocket2.recv()
                                    symmetric_key, symmetric_iv, data = decryptMsg(response, client_private_key)
                                    print(data)

                                else:
                                    message={"action":act}
                                    if act=="1": # Auction creation
                                        print("Fill in the form below to create an auction (* means the field is mandatory)")
                                        atype = input("*Auction Type (1-English Auction, 2-Reversed Auction, 3-BlindAuction): ")
                                        minimumV = float(input("*Minimum Value: "))
                                        if atype=="2":
                                            startingV = float(input("*Starting Value: "))
                                            marginV = float(input("*Margin Value: "))
                                            message["auction"]={"type":atype,"minv":minimumV,"startv":startingV,"marginv":marginV,"name":input("*Name: "),"descr":input("*Description: "),"serialNum":input("*Serial Number: "), "time":str(datetime.now()+timedelta(minutes=int(input("*Valid Minutes: "))))}
                                        else:
                                            message["auction"]={"type":atype,"minv":minimumV,"name":input("*Name: "),"descr":input("*Description: "),"serialNum":input("*Serial Number: "), "time":str(datetime.now()+timedelta(minutes=int(input("*Valid Minutes: "))))}
                                        
                                        limitUsers=input("Limit of Users: ")
                                        if limitUsers=="":
                                            limitUsers="-1"
                                        usersBids=input("Limit of Bids per User: ")
                                        if usersBids=="":
                                           usersBids="-1"
                                        message["auction"]["limitusers"]=int(limitUsers)
                                        message["auction"]["userbids"]=int(usersBids)
                                        
                                        print("Validation function (write a function called 'validate' accepting only one argument 'bid' with Python3 syntax, write 'end' to finish or skip this step):")
                                        validation_func = ""
                                        input_str = input()
                                        while input_str != "end":
                                            validation_func += input_str + "\n"
                                            input_str = input()
                                        if validation_func != "":
                                            validation_func += "\nvalidate(bid)\n"
                                            #print(validation_func)
                                            #exec(validation_func, {'bid':bid_obj})
                                        message["auction"]["validation"]=validation_func
                                        
                                        print("Manipulation functions (write a function called 'manipulate' accepting only one argument 'bid' with Python3 syntax, write 'end' to finish or skip this step):")
                                        manipulation_func = ""
                                        input_str = input()
                                        while input_str != "end":
                                            manipulation_func += input_str + "\n"
                                            input_str = input()
                                        if manipulation_func != "":
                                            manipulation_func += "\nvalidate(bid)\n"
                                            #print(manipulation_func)
                                            #exec(manipulation_func, {'bid':bid_obj})
                                        message["auction"]["manipulation"]=manipulation_func
                                        
                                    if act=="2":
                                        message["auction"]={"serialNum":input("*Serial Number: ")}

                                    # Send encrypted message
                                    message["key"]=client_public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("utf-8")
                                    out = encryptMsg(json.dumps(message), manager_public_key)
                                    await websocket1.send(out)
                                    
                                    # Receive and decrypt response message
                                    response = await websocket1.recv()
                                    symmetric_key, symmetric_iv, data = decryptMsg(response, client_private_key)
                                    print(data)

                                act = input("0-Leave\n1-Create Auction\n2-Close Auction\n3-List Auctions\n4-List Bids of Auction\n5-List Bids by Client\n6-Check Outcome\n7-Make Bid\nAction: ")

asyncio.get_event_loop().run_until_complete(interface())
