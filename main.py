from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import random
import mysql.connector
import psycopg2.extras

app = FastAPI()

# Add CORS middleware allowing any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections:list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_json({'message': message})

    async def broadcastMessage(self, message: str, websocket: WebSocket):
        for connection in self.active_connections:
            if connection != websocket:
                await connection.send_json({'message': message})

    async def broadcastPhoto(self, showPhoto: bool, websocket: WebSocket):
        for connection in self.active_connections:
            await connection.send_json({'showPhoto': showPhoto})

connectionManager = ConnectionManager()

# MySQL connection parameters
host = 'localhost'
user = 'root'
password = 'root'
database = 'istatus'

@app.get('/')
async def root(): 
    return HTMLResponse("""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Python API</title>
        </head>
        <body style='background:black; color:dodgerblue'>
            <h1>Welcome to Shazeb's Python API</h1>
        </body>
        </html>
        """)

@app.get('/random/{limit}')
async def get_random(limit: int):
    rn:int = random.randint(0, limit)
    return {
        'number': rn,
        'limit': limit
    }

@app.get('/blogs')
async def get_istatus():
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )    
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM blogsite.blogs;')
    records = cursor.fetchall()  
    data = []   
    for record in records:
        data.append(record) 

    # close database connection
    cursor.close()
    connection.close()
    return {'data': data}

@app.get('/postgres')
async def example_postgres():
    conn = psycopg2.connect(
    host="localhost",
    dbname="postgres",
    user="postgres",
    password="",
    port=5432)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""CREATE TABLE IF NOT EXISTS hosts (
        host_id SERIAL PRIMARY KEY,
        host_name VARCHAR(255),
        host_key VARCHAR(50)
    );
    """)

    cur.execute("""CREATE TABLE IF NOT EXISTS voters (
        voter_id SERIAL PRIMARY KEY,
        voter_name VARCHAR(255),
        voter_key VARCHAR(50),
        voter_host_id INT REFERENCES hosts(host_id)
    );
    """)

    cur.execute("""SELECT * FROM voters ORDER BY voter_name ASC;""")

    voters = []
    for row in cur.fetchall():
        voters.append({
            "voter_name": row['voter_name'],
            "voter_key": row['voter_key']
        })

    conn.commit()
    cur.close()
    conn.close()

    return {"voters": voters}

# WebSocket endpoint 
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    client_id = None
    await connectionManager.connect(websocket)  
    try:
        while True:
            data = await websocket.receive_json() 

            if 'showPhoto' in data:
                showPhoto = data.get('showPhoto')
                await connectionManager.broadcastPhoto(not showPhoto, websocket)

            elif 'message' in data:
                client_id = data.get('client_id') 
                message = data.get('message') 

                print(f'#{client_id} says: {message}') 

                await connectionManager.broadcastMessage(f'#{client_id} says: {message}', websocket)

    # Catch exceptions
    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)
        print(f'#{client_id} has disconnected')
        await connectionManager.broadcastMessage(f'#{client_id} has disconnected', websocket) 