from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2 import sql
import os
import base64
from datetime import datetime

app = FastAPI()

def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        raise HTTPException(status_code=500, detail="数据库连接失败")

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS user_files (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            filetype VARCHAR(100) NOT NULL,
            filedata TEXT NOT NULL,
            uploadtime TIMESTAMP DEFAULT NOW()
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        conn.close()
        print("数据库表初始化成功")
    except Exception as e:
        print(f"初始化数据库失败: {e}")

init_database()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = file.filename
        filetype = file.content_type or "application/octet-stream"
        filedata = base64.b64encode(content).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO user_files (filename, filetype, filedata)
        VALUES (%s, %s, %s)
        RETURNING id, uploadtime
        """
        cursor.execute(insert_query, (filename, filetype, filedata))
        result = cursor.fetchone()
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return JSONResponse(content={
            "status": "success",
            "file_id": result[0],
            "filename": filename,
            "filetype": filetype,
            "uploadtime": result[1].isoformat()
        })
    except Exception as e:
        print(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.get("/api/files")
async def get_files():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, filename, filetype, uploadtime FROM user_files ORDER BY uploadtime DESC")
        files = cursor.fetchall()
        
        file_list = []
        for file in files:
            file_list.append({
                "id": file[0],
                "filename": file[1],
                "filetype": file[2],
                "uploadtime": file[3].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return JSONResponse(content={"status": "success", "files": file_list})
    except Exception as e:
        print(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@app.get("/api/files/{file_id}")
async def get_file(file_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT filename, filetype, filedata FROM user_files WHERE id = %s", (file_id,))
        file = cursor.fetchone()
        
        if not file:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        filename, filetype, filedata = file
        content = base64.b64decode(filedata)
        
        cursor.close()
        conn.close()
        
        from fastapi.responses import Response
        return Response(content=content, media_type=filetype, headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM user_files WHERE id = %s", (file_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        cursor.close()
        conn.close()
        
        return JSONResponse(content={"status": "success", "message": "文件删除成功"})
    except HTTPException:
        raise
    except Exception as e:
        print(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
