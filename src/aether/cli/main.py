import typer
import httpx
from aether.config import settings

app = typer.Typer()

@app.command()
def health():
    """Check API health"""
    url = f"http://{settings.API_HOST}:{settings.API_PORT}/health"
    try:
        response = httpx.get(url)
        typer.echo(f"API Health: {response.json()['status']}")
    except Exception as e:
        typer.echo(f"Error: {e}")

if __name__ == "__main__":
    app()
