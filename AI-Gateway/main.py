@app.post("/chat")
def chat(req: ChatRequest):

    payload = {
        "model": MODEL_NAME,
        "prompt": req.message,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        return {
            "question": req.message,
            "answer": data.get("response", "")
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menghubungi Ollama: {e}"
        )