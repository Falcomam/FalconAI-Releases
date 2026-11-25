"""Original procedural cartoon cards, not generative AI video.

Pillow is required. All geometry is authored here; no external artwork.
The same story seed gives one recurring creature across six different poses.
"""
import hashlib
import random
from PIL import Image, ImageDraw

SIZE = (720, 1280)
SETTINGS = ("kitchen", "city", "moon", "gym", "ocean", "desert", "office")
ACTIONS = ("stand", "jump", "run", "panic", "celebrate", "fall")

def render_scene(key, index, setting, action, destination):
    if setting not in SETTINGS or action not in ACTIONS or not 0 <= index < 6:
        raise ValueError("Unknown scene choice")
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest(), 16))
    body = tuple(rng.randrange(90, 230) for _ in range(3))
    accent = tuple(255-c//2 for c in body)
    shape = rng.choice(("round", "box"))
    palette = {"kitchen": (60,38,75), "city": (33,53,85), "moon": (15,18,45),
               "gym": (70,36,43), "ocean": (15,72,105), "desert": (116,62,45),
               "office": (38,62,66)}
    bg = palette[setting]
    image = Image.new("RGB", SIZE, bg)
    d = ImageDraw.Draw(image)
    d.ellipse((-180,280,900,1360), fill=tuple(min(255,c+25) for c in bg))
    d.rectangle((0,900,720,1280),fill=tuple(max(0,c-13) for c in bg))
    if setting == "city" or setting == "office":
        for k in range(6):
            x = 120*k
            h = 260 + (k*137)%360
            d.rectangle((x,900-h,x+105,900), fill=tuple(max(0,c-20) for c in bg))
            for y in range(930-h,850,75):
                d.rectangle((x+20,y,x+42,y+28), fill=accent)
    elif setting == "moon":
        for k in range(45):
            x,y = (k*137)%720,(k*97)%720
            d.ellipse((x,y,x+4,y+4),fill="white")
        d.ellipse((500,100,680,280),fill=(240,225,174))
    elif setting == "ocean":
        for k in range(6):
            d.arc((-100,200+90*k,820,370+90*k),0,180,fill=(70,140,175),width=9)
    elif setting == "desert":
        d.polygon([(0,900),(170,560),(370,900)],fill=(173,103,62))
        d.polygon([(330,900),(570,510),(720,900)],fill=(185,119,70))
    else:
        for k in range(5):
            x=40+k*145
            d.rounded_rectangle((x,180,x+110,390),radius=18,fill=tuple(min(255,c+36) for c in bg))
    x=360+(-65 if action=="run" else 0)
    y=665+({"jump":-120,"fall":135,"panic":-20}.get(action,0))
    ink=(20,16,28)
    d.ellipse((x-175,920,x+175,963),fill=ink)
    d.line((x-85,y+140,x-110,y+220,x-165,y+230),fill=ink,width=28)
    d.line((x+85,y+140,x+115,y+220,x+160,y+230),fill=ink,width=28)
    arms_up=action in ("jump","panic","celebrate")
    for sign in (-1,1):
        d.line((x+sign*135,y,x+sign*210,y+(-125 if arms_up else 65)),fill=ink,width=27)
        xx=x+sign*210; yy=y+(-125 if arms_up else 65)
        d.ellipse((xx-28,yy-28,xx+28,yy+28),fill=accent,outline=ink,width=7)
        d.polygon([(x+sign*55,y-140),(x+sign*150,y-245),(x+sign*165,y-110)],fill=accent,outline=ink,width=8)
    bounds=(x-155,y-165,x+155,y+160)
    if shape=="round":
        d.ellipse(bounds,fill=body,outline=ink,width=12)
    else:
        d.rounded_rectangle(bounds,radius=55,fill=body,outline=ink,width=12)
    for sign in (-1,1):
        cx=x+sign*65
        d.ellipse((cx-43,y-75,cx+43,y+15),fill="white",outline=ink,width=6)
        offset=12 if action=="run" else 0
        d.ellipse((cx-15+offset,y-47,cx+15+offset,y-10),fill=ink)
    if action in ("panic","fall"):
        d.ellipse((x-33,y+36,x+33,y+105),fill=ink)
    else:
        d.arc((x-52,y+15,x+52,y+85),0,180,fill=ink,width=12)
    image.save(destination, format="PNG")
