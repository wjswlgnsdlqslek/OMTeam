from fastapi import FastAPI

from app.api.endpoints import daily_missions, daily_analysis, weekly_analysis, chat

app = FastAPI(
    title="OMTeam AI Server",
    description="AI Agent Orchestration for Daily Missions, Feedback, and Chat",
    version="0.1.0",
)

@app.get("/")
async def read_root():
    return {"message": "OMTeam AI Server is running!"}

app.include_router(daily_missions.router)
app.include_router(daily_analysis.router)
app.include_router(weekly_analysis.router)
app.include_router(chat.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)