"""Build the app's own icon (geometric source; no external artwork)."""
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parent.parent / 'assets'
folder.mkdir(exist_ok=True)
icon = Image.new('RGBA', (1024, 1024))
draw = ImageDraw.Draw(icon)
draw.rounded_rectangle((32, 32, 992, 992), radius=200, fill='#2463a6')
draw.rounded_rectangle((200, 260, 680, 730), radius=64, outline='white', width=38)
draw.polygon([(366, 385), (366, 605), (555, 495)], fill='white')
draw.rounded_rectangle((674, 355, 720, 764), radius=20, fill='#ffcc66')
draw.polygon([(700, 355), (855, 300), (855, 377), (700, 432)], fill='#ffcc66')
draw.ellipse((554, 686, 720, 815), fill='#ffcc66')
icon.save(folder / 'icon.png')
icon.save(folder / 'icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
icon.save(folder / 'icon.icns')
