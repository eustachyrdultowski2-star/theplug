#!/usr/bin/env python3
"""Download the selected real Instagram product photos into assets/photos/."""
import os, urllib.request

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "photos")
os.makedirs(DIR, exist_ok=True)

IMAGES = {
 "mn1.jpg": "https://scontent-syd2-1.cdninstagram.com/v/t51.82787-15/731541309_18026978546844934_2897280398994250937_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=scontent-syd2-1.cdninstagram.com&_nc_cat=110&_nc_oc=Q6cZ2gEmhr_-dQcEQVaN3P51jP0SPu7kIeEu-xmQX0dcXY4xy0ijgfXs0JnPG3d2z80FUn0&_nc_ohc=JpMlJTEwdbsQ7kNvwGks169&_nc_gid=l-dddWnQ8HeG4EyrTiTqyg&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQFfp3d888stlun-0WQZqGgzhgXtaNdrPJLIJ8JHrNq78A&oe=6A875EA2&_nc_sid=c6f216",
 "mn2.jpg": "https://instagram.fstr1-1.fna.fbcdn.net/v/t51.82787-15/715950512_18023997041844934_5883772282003453404_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=instagram.fstr1-1.fna.fbcdn.net&_nc_cat=110&_nc_oc=Q6cZ2gGNu0_ALpcgnB60oQSBzfLoX6-A4bPDlBw8QvfYMOrdOVMrDCghdSgRU6iU9jRN18o&_nc_ohc=yo-p4DRXBWcQ7kNvwGS8O2R&_nc_gid=5SMmtZwvXEuKVpGS87Bauw&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQHnVQqjupDApvhO2WbFXmiy65eWfwAjDAKA8iwRHiUUhA&oe=6A874DB2&_nc_sid=c6f216",
 "mn3.jpg": "https://scontent-icn2-1.cdninstagram.com/v/t51.82787-15/724429891_18025643975844934_7544332095838471939_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=scontent-icn2-1.cdninstagram.com&_nc_cat=110&_nc_oc=Q6cZ2gEP_-Dhq90Y0r_cAmCvu_6NtbsxtE780pkqnuxSvWl9Lv0-R-Fk1ACx10-3JpAklAQ&_nc_ohc=-prZdRFMP_AQ7kNvwGLeJEx&_nc_gid=AN4kMlzsSqnruvQ6t1lsrQ&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQEFllmvDz-_IFQWZEORj5BmGA96mgiPJ6BtoJdjIWP5bA&oe=6A875D50&_nc_sid=c6f216",
 "sdn1.jpg": "https://scontent-dus1-1.cdninstagram.com/v/t51.82787-15/669776915_18108437359854201_3804176908423003411_n.jpg?stp=dst-jpg_e15_tt6&_nc_ht=scontent-dus1-1.cdninstagram.com&_nc_cat=109&_nc_oc=Q6cZ2gEnBPfIJK3RxFRE5s-Ev5iI-4yCNBf9LxoAulwaGXRGhVaxCa8byto7s6A5_s2EjOU&_nc_ohc=8OjMdMd-MuIQ7kNvwFdK9SN&_nc_gid=kCaZyaAh70W1XRuvmPe8XQ&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQG9QYR10ifm7oetqmANJ14SHy2YM7wVQTy-LjMMl_dTkA&oe=6A877446&_nc_sid=c6f216",
 "sdn2.jpg": "https://scontent-ord5-1.cdninstagram.com/v/t51.82787-15/741679126_18117332467854201_3147409312757913075_n.jpg?stp=dst-jpg_e15_tt6&_nc_ht=scontent-ord5-1.cdninstagram.com&_nc_cat=109&_nc_oc=Q6cZ2gEXlTHNDPUMQYy7qG0ZVbqohFQMNvmQd5xp4v_OS9suF7sQVA8SHSM5HSxRsNpOUcsKYovNe-iKuAngT-nBBWSl&_nc_ohc=I5zyZgqIPtcQ7kNvwE82EBR&_nc_gid=vQnHC6C8jOT2i4-UqlmGDw&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQG0kNaaXaN7jS4y65fzxKHL7YFeP4ck4vmEOy1BZ0--Qg&oe=6A877618&_nc_sid=c6f216",
 "sdn3.jpg": "https://instagram.fbcn10-1.fna.fbcdn.net/v/t51.82787-15/683625341_18110072692854201_1351624466344570634_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=instagram.fbcn10-1.fna.fbcdn.net&_nc_cat=109&_nc_oc=Q6cZ2gGzhy-t42RZdQfI_U5ZrOG4RPllZOn3KehZ3RDcGMmNBlA9pStJfYB6NPG0TZmJe6U&_nc_ohc=JvpXBzEnxZkQ7kNvwE3QQbt&_nc_gid=AzG-PUG5vXL7CfmeMXe0tQ&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQGsbsWneYZQ5hL3SjHdQyr5lSj7jTvqCwOwWDWfGqKVXA&oe=6A876242&_nc_sid=c6f216",
 "uf1.jpg": "https://scontent-fra5-1.cdninstagram.com/v/t51.82787-15/670834366_17948382261187284_2902068991567336699_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=scontent-fra5-1.cdninstagram.com&_nc_cat=100&_nc_oc=Q6cZ2gF97g21mnb3SGBIL035dJ9chw8VzNn7Mid5l9Q_odrWAuhJGX8F8slT_Sz40PfRP58&_nc_ohc=n1gcMcDZ4KsQ7kNvwGPbxTt&_nc_gid=zTtgv7seeCwdP-x6y-Rqtw&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQHZ1ATuRTcSFkqXGGJyXaVU4tTxNIy1xPHu5OMRqK2yLg&oe=6A877848&_nc_sid=c6f216",
 "uf2.jpg": "https://instagram.flhr12-1.fna.fbcdn.net/v/t51.82787-15/708571443_17950458870187284_3682716522754082046_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=instagram.flhr12-1.fna.fbcdn.net&_nc_cat=100&_nc_oc=Q6cZ2gFXE1PfcMm10JOFetGHqAmdNX133Lul8D7W-Fwc3ruodoYOXRzVcKS2x06Jec2uPfY&_nc_ohc=toiCaYFqUzsQ7kNvwEnnNGo&_nc_gid=H2cKbe4O0RG_JILjpmLE7Q&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQGbE84W7g--45UzmCUjg96NNuNXt6fcHxHyf0v-fIm_ow&oe=6A87524E&_nc_sid=c6f216",
 "uf3.jpg": "https://scontent-icn2-1.cdninstagram.com/v/t51.82787-15/709770763_17950603824187284_3274035284411768341_n.jpg?stp=dst-jpg_e35_p1080x1080_sh2.08_tt6&_nc_ht=scontent-icn2-1.cdninstagram.com&_nc_cat=100&_nc_oc=Q6cZ2gFXSGCuS83fsdfE3wAttgISkhS-sNUA5GXIc3GyS4_0zM2NhWbhadkBVqFTaPgK088&_nc_ohc=VW6M9oUMp6cQ7kNvwHbrClm&_nc_gid=2C4yw-iArrzQwGdEXcJ0_g&edm=ADp7STQBAAAA&ccb=7-5&oh=00_AQHaBN5-IG8-WLurAlKd2-4MKoag1RVJPdX1YYc6OCX2lQ&oe=6A876BB7&_nc_sid=c6f216",
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
for name, url in IMAGES.items():
    dst = os.path.join(DIR, name)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with open(dst, "wb") as f:
            f.write(data)
        print(f"OK  {name}  {len(data)//1024} KB")
    except Exception as e:
        print(f"ERR {name}  {e}")
