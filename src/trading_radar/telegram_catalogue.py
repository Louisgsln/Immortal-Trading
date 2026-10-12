"""Small explicit pages of every stored score, without replaying the alert journal."""

from trading_radar.config import Config
from trading_radar.dashboard_applications import _connection
from trading_radar.models import Job
from trading_radar.notifications import TelegramNotifier
from trading_radar.telegram_cards import application_keyboard, format_alert
from trading_radar.wishlist import list_wishlist

PAGE_SIZE = 5


async def send_catalogue(
    config: Config, notifier: TelegramNotifier, page: int, *, wished: bool = False
) -> None:
    saved = {item["job_id"] for item in list_wishlist(config)}
    with _connection(config) as db:
        rows = db.execute(
            "SELECT j.payload,a.status FROM jobs j JOIN applications a ON a.job_id=j.id ORDER BY j.first_seen DESC,j.id"
        ).fetchall()
        if wished:
            rows = [row for row in rows if Job.model_validate_json(row[0]).id in saved]
        total = len(rows)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        if page > pages:
            await notifier.send_text(
                f"Page inexistante. Utilise /{'souhaits' if wished else 'offres'} 1 · {pages} page(s)."
            )
            return
        selected = [
            (Job.model_validate_json(row[0]), row[1])
            for row in rows[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        ]
    command = "souhaits" if wished else "offres"
    title = "⭐ Liste de souhaits" if wished else "📚 Toutes les offres · tous scores, même 0"
    await notifier.send_text(
        f"{title}\n{total} offre(s) · page {page}/{pages}\n"
        + (f"Suite : /{command} {page + 1}" if page < pages else "Fin de la liste.")
    )
    for job, status in selected:
        await notifier.send_text(
            format_alert(job, "catalogue"),
            parse_mode="HTML",
            reply_markup=application_keyboard(
                job.id,
                job.apply_url,
                notifier.token,
                notifier.chat_id,
                applied=status == "Applied",
                wished=job.id in saved,
            ),
        )
