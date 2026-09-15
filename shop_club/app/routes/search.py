# shop_club/app/routes/search.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from app.auth import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/search")
async def search_page(request: Request, user=Depends(get_current_user_optional)):
    return templates.TemplateResponse(
        request=request,          # 👈 Передаем request отдельно первым именованным аргументом
        name="search.html",       # 👈 Передаем имя шаблона отдельно
        context={                 # 👈 Все остальные переменные складываем в context
            "current_user": user,
            "title": "Поиск аналогов"
        }
    )
