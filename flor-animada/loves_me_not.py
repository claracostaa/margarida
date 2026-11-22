"""Loves me, loves me not - margarida em pixel art (tkinter + Pillow + numpy)

Instalar:  pip install pillow numpy
Rodar:     python loves_me_not.py
Teclas:    clique na pétala = arrancar | ESPACO = recomeçar   |   ESC = sair
"""
import math
import random
import tkinter as tk

import numpy as np
from PIL import Image, ImageDraw, ImageTk

# ---------- configuração ----------
W, H, SCALE = 120, 200, 4          # resolução lógica e zoom (janela 480x800)
GROUND = 166                        # linha do chão
FLOWER = (60, 70)                   # centro da flor
MOON = (101, 34)
N_PETALS = 13                       # ímpar: começa e termina em "LOVES ME"
PETAL_LEN, PETAL_WID = 22, 8
FRAME_MS = 33

PETAL = (205, 228, 248)
PETAL_EDGE = (150, 190, 228)
STEM = (46, 140, 60)
LEAF = (64, 170, 74)
LEAF_EDGE = (30, 105, 50)
PINK = (232, 120, 172)
BLUE = (150, 195, 245)
HEARTS = [(236, 72, 112), (255, 112, 152), (214, 52, 92)]

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                  [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0

FONT = {
    "L": ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"],
    "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "V": ["X...X", "X...X", "X...X", "X...X", "X...X", ".X.X.", "..X.."],
    "E": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"],
    "S": [".XXXX", "X....", "X....", ".XXX.", "....X", "....X", "XXXX."],
    "M": ["X...X", "XX.XX", "X.X.X", "X...X", "X...X", "X...X", "X...X"],
    "N": ["X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"],
    "T": ["XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."],
    " ": ["....."] * 7,
}
HEART = ["·XX·XX·", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]


# ---------- fundo (pré-renderizado, com dithering) ----------
def dither(rgb, step=22):
    th = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W, None] - 0.5
    return np.clip(np.floor((rgb + th * step) / step + 0.5) * step, 0, 255)


def build_background():
    ys, xs = np.mgrid[0:H, 0:W]
    t = np.clip(ys / GROUND, 0, 1)[..., None]
    top, mid, bot = np.array([8, 12, 55.]), np.array([28, 50, 150.]), np.array([72, 112, 205.])
    sky = np.where(t < 0.6, top + (mid - top) * (t / 0.6), mid + (bot - mid) * ((t - 0.6) / 0.4))
    glow = np.clip(1 - np.hypot(xs - MOON[0], ys - MOON[1]) / 22, 0, 1) ** 2 * 80
    sky = sky + glow[..., None] * np.array([1, 0.95, 0.55])
    gt = np.clip((ys - GROUND) / (H - GROUND), 0, 1)[..., None]
    ground = np.array([62, 155, 62.]) + (np.array([20, 80, 45.]) - np.array([62, 155, 62.])) * gt
    img = dither(sky)
    for x in range(W):                                   # colinas
        y1 = int(146 + 8 * math.sin(x * .05) + 4 * math.sin(x * .14 + 1))
        y2 = int(154 + 5 * math.sin(x * .07 + 2) + 3 * math.sin(x * .2))
        img[y1:GROUND, x] = (36, 38, 104)
        img[y2:GROUND, x] = (26, 42, 100)
    img[GROUND:] = dither(ground)[GROUND:]
    rng = random.Random(7)
    for _ in range(260):                                 # tufos de grama
        x, h = rng.randrange(W), rng.randint(2, 5)
        c = rng.choice([(120, 200, 90), (90, 180, 80), (60, 150, 70)])
        img[GROUND - h:GROUND + rng.randint(0, 2), x] = c
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.ellipse((MOON[0] - 6, MOON[1] - 6, MOON[0] + 6, MOON[1] + 6), fill=(240, 236, 172))
    for p in [(-2, -2), (2, 1), (-1, 3), (3, -3)]:
        d.point((MOON[0] + p[0], MOON[1] + p[1]), (214, 206, 142))
    return im


def make_stars():
    rng = random.Random(3)
    stars = []
    while len(stars) < 45:
        x, y = rng.randrange(W), rng.randrange(0, 135)
        if math.hypot(x - MOON[0], y - MOON[1]) > 16:
            stars.append((x, y, rng.uniform(0, 6.28)))
    return stars


def blob(cx, cy, ang, length, width, tip=0.25):
    """Elipse orientada (pétala/folha), mais larga na ponta."""
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for k in range(16):
        th = k * 2 * math.pi / 16
        u = math.cos(th) * length / 2
        v = math.sin(th) * width / 2 * (0.85 + tip * u / (length / 2))
        pts.append((cx + u * ca - v * sa, cy + u * sa + v * ca))
    return pts


def petal_bottom(p, width):
    """Retorna a parte mais baixa da pétala no seu angulo atual."""
    return max(point[1] for point in blob(p["x"], p["y"], p["ang"], PETAL_LEN, width))


def resting_y(ang, width):
    """Distancia do centro ao ponto mais baixo da pétala."""
    points = blob(0, 0, ang, PETAL_LEN, width)
    return GROUND - max(point[1] for point in points)


# ---------- cena (lógica + desenho) ----------
class Scene:
    def __init__(self):
        self.bg = build_background()
        self.stars = make_stars()
        self.reset()

    def reset(self):
        self.t = 0
        self.count = 0
        self.text = ""
        self.phase = "pluck"
        self.phase_t = 0
        self.fallen, self.hearts = [], []
        step = 2 * math.pi / N_PETALS
        self.angles = [i * step - math.pi / 2 + random.uniform(-.08, .08) for i in range(N_PETALS)]
        self.remaining = list(range(N_PETALS))

    def head(self):
        return FLOWER[0] + 1.5 * math.sin(self.t * 0.03), FLOWER[1]

    def pluck(self, i):
        self.remaining.remove(i)
        self.count += 1
        self.text = "LOVES ME" if self.count % 2 else "LOVES ME NOT"
        a, (hx, hy) = self.angles[i], self.head()
        r = 5 + PETAL_LEN / 2
        self.fallen.append(dict(
            x=hx + math.cos(a) * r, y=hy + math.sin(a) * r, ang=a,
            vx=random.uniform(-.5, .5) + math.cos(a) * .4, vy=-.5,
            spin=random.uniform(-.12, .12), ph=random.uniform(0, 6.28),
            landed=False))

    def click(self, x, y):
        """x, y em pixels lógicos. Arranca a pétala clicada."""
        if self.phase == "hearts":
            if self.phase_t > 60:
                self.reset()
            return
        hx, hy = self.head()
        r = 5 + PETAL_LEN / 2
        best, best_d = None, 1e9
        for i in self.remaining:
            a = self.angles[i]
            dx, dy = x - (hx + math.cos(a) * r), y - (hy + math.sin(a) * r)
            u = dx * math.cos(a) + dy * math.sin(a)
            v = -dx * math.sin(a) + dy * math.cos(a)
            if (u / (PETAL_LEN / 2 + 2)) ** 2 + (v / (PETAL_WID / 2 + 2)) ** 2 <= 1 and u * u + v * v < best_d:
                best, best_d = i, u * u + v * v
        if best is not None:
            self.pluck(best)
            if not self.remaining:
                self.phase, self.phase_t = "hearts", 0

    def update(self):
        self.t += 1
        for p in self.fallen:
            if p["landed"]:
                continue
            p["vy"] = min(p["vy"] + .04, .9)
            p["x"] += p["vx"] * .6 + math.sin(self.t * .1 + p["ph"]) * .35
            p["y"] += p["vy"]
            p["ang"] += p["spin"]
            p["x"] = min(W - PETAL_LEN / 2 - 1, max(PETAL_LEN / 2 + 1, p["x"]))
            if petal_bottom(p, PETAL_WID) >= GROUND:
                p["ang"] = random.choice([0, math.pi]) + random.uniform(-.25, .25)
                p["y"] = resting_y(p["ang"], 5)
                p["vx"], p["vy"], p["spin"], p["landed"] = 0, 0, 0, True
        if self.phase == "hearts":
            self.phase_t += 1
            if 15 < self.phase_t < 170 and self.phase_t % 5 == 0:
                hx, hy = self.head()
                self.hearts.append(dict(x=hx + random.uniform(-9, 9), y=hy + random.uniform(-4, 8),
                                        vy=-random.uniform(.3, .6), life=random.randint(80, 120),
                                        ph=random.uniform(0, 6.28), c=random.choice(HEARTS)))
            if self.phase_t > 300:
                self.reset()
        for h in self.hearts:
            h["y"] += h["vy"]
            h["x"] += math.sin(self.t * .07 + h["ph"]) * .25
            h["life"] -= 1
        self.hearts = [h for h in self.hearts if h["life"] > 0]

    def render(self):
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        for x, y, ph in self.stars:
            b = int(165 + 80 * math.sin(self.t * .08 + ph))
            d.point((x, y), (b, b, min(255, b + 30)))
        hx, hy = self.head()
        top_y, base_y = hy + 4, GROUND + 2
        stem = []
        for k in range(21):
            s = k / 20
            stem.append((60 + (hx - 60) * (1 - s) ** 2 + 2.5 * math.sin(s * math.pi),
                         top_y + (base_y - top_y) * s))
        d.line(stem, fill=STEM, width=2)
        for s, ang in ((0.58, math.radians(-150)), (0.78, math.radians(-30))):
            bx, by = stem[int(s * 20)]
            cx, cy = bx + math.cos(ang) * 9, by + math.sin(ang) * 9
            d.polygon(blob(cx, cy, ang, 18, 8, .1), fill=LEAF, outline=LEAF_EDGE)
        for p in self.fallen:                                    # pétalas no chão
            if p["landed"]:
                d.polygon(blob(p["x"], p["y"], p["ang"], PETAL_LEN, 5), fill=PETAL, outline=PETAL_EDGE)
        for i in self.remaining:                                 # pétalas na flor
            a, r = self.angles[i], 5 + PETAL_LEN / 2
            d.polygon(blob(hx + math.cos(a) * r, hy + math.sin(a) * r, a, PETAL_LEN, PETAL_WID),
                      fill=PETAL, outline=PETAL_EDGE)
        d.ellipse((hx - 5, hy - 5, hx + 5, hy + 5), fill=(232, 150, 50), outline=(110, 70, 40))
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if (dx + dy) % 2 == 0 and dx * dx + dy * dy <= 16:
                    d.point((hx + dx, hy + dy), (206, 120, 40) if dy > 0 else (250, 192, 92))
        for p in self.fallen:                                    # pétalas caindo
            if not p["landed"]:
                d.polygon(blob(p["x"], p["y"], p["ang"], PETAL_LEN, PETAL_WID), fill=PETAL, outline=PETAL_EDGE)
        for h in self.hearts:
            if h["life"] < 20 and h["life"] % 2:
                continue
            for r, row in enumerate(HEART):
                for c, ch in enumerate(row):
                    if ch == "X":
                        d.point((int(h["x"]) + c, int(h["y"]) + r), h["c"])
        if self.text:
            color = PINK if self.text == "LOVES ME" else BLUE
            x0 = (W - (len(self.text) * 6 - 1)) // 2
            for n, ch in enumerate(self.text):
                for r, row in enumerate(FONT[ch]):
                    for c, v in enumerate(row):
                        if v == "X":
                            d.point((x0 + n * 6 + c, 14 + r), color)
        return img


# ---------- janela ----------
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Loves me, loves me not")
        self.root.resizable(False, False)
        self.scene = Scene()
        self.label = tk.Label(self.root, bd=0, cursor="hand2")
        self.label.pack()
        self.root.bind("<space>", lambda e: self.scene.reset())
        self.root.bind("<Button-1>", lambda e: self.scene.click(e.x // SCALE, e.y // SCALE))
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.tick()
        self.root.mainloop()

    def tick(self):
        self.scene.update()
        big = self.scene.render().resize((W * SCALE, H * SCALE), Image.NEAREST)
        self.photo = ImageTk.PhotoImage(big)
        self.label.configure(image=self.photo)
        self.root.after(FRAME_MS, self.tick)


if __name__ == "__main__":
    App()