import io
import matplotlib.pyplot as plt
from matplotlib import rcParams
import pandas as pd

def render_table_image(records: list[dict]):
    """
    Создаёт PNG с таблицей рекордов.
    Принимает список словарей с ключами: user, movement, date, weight
    Возвращает BytesIO-буфер для отправки в Telegram.
    """

    # Если записей нет — возвращаем картинку "Нет записей"
    if not records:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.axis("off")
        ax.text(0.5, 0.5, "Нет записей", ha="center", va="center", fontsize=14)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    # Преобразуем данные в DataFrame
    df = pd.DataFrame(records)[["user", "movement", "date", "weight"]]
    df = df.rename(columns={
        "user": "Имя",
        "movement": "Движение",
        "date": "Дата",
        "weight": "Вес (кг)"
    })

    # Настройки matplotlib
    rcParams.update({
        'font.size': 10,
        'axes.titlesize': 12,
        'axes.labelsize': 10,
        'figure.autolayout': True,
    })

    # Создание таблицы
    fig, ax = plt.subplots(figsize=(10, max(2.5, 0.4 * len(df))))
    ax.axis("off")

    ax.text(
        0.5, 1.03, "Таблица рекордов",
        ha='center', va='bottom',
        fontsize=14, fontweight='bold',
        transform=ax.transAxes
    )

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc='center',
        loc='center'
    )

    # Стилизация таблицы
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#2E86AB')
        else:
            cell.set_facecolor('#F7FAFC' if row % 2 == 0 else 'white')
        cell.set_edgecolor('#CCCCCC')

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.2)

    # Сохранение изображения в буфер
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf
