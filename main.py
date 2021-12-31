import os
import sys
import pygame
mixer = pygame.mixer
mixer.init()
win = mixer.Sound('data/sounds/win.wav')
lvl_start = mixer.Sound('data/sounds/lvl_start.wav')
gas = mixer.Sound('data/sounds/gas.wav')
bg_bike = mixer.Sound('data/sounds/bike.wav')
not_gas = mixer.Sound('data/sounds/not_gas.wav')
bg_music = mixer.Sound('data/sounds/bg_music.mp3')
your_levels = 0  # сколько уровней прошёл
your_record = 0  # максимум очков
prev_record = 0
compl_game = False  # прохождение на 100%
levels_amount = 2
try:
    with open('data/save.txt', 'r') as f:
        s = f.read().split('\n')  # строки еще делятся на до равно и после, после - это значение
        your_levels = int(s[0].split('=')[1])
        your_record = int(s[1].split('=')[1])
        prev_record = your_record  # это надо для сравнения старого и нового
        compl_game = s[2].split('=')[1] == 'True'
except FileNotFoundError:
    with open('crash.txt', 'w') as f:
        f.write('Cannot find save.txt')
    pygame.quit()
    sys.exit()
WIDTH = 640
HEIGHT = 480
screen_size = (WIDTH, HEIGHT)
FPS = 50
tile_width = tile_height = 50
pygame.init()
screen = pygame.display.set_mode(screen_size)
pygame.display.set_caption('Hill Expert')
clock = pygame.time.Clock()


def click_rect(xy, xywh):
    x, y = xy
    x1, y1, w, h = xywh
    return 0 <= x - x1 <= w and 0 <= y - y1 <= h


def terminate():
    pygame.quit()
    sys.exit()


def load_image(name, color_key=None):
    fullname = os.path.join('data/images', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Не могу загрузить изображение:', name)
        raise SystemExit(message)
    if color_key is not None:
        if color_key == -1:
            color_key = image.get_at((0, 0))
            image.set_colorkey(color_key)
        else:
            image.set_colorkey(image.get_at((49, 0)))
    else:
        image = image.convert_alpha()
    return image


tile_images = {'floor': load_image('floor.png'),
               'brick': load_image('brick.png'),
               'up': load_image('up.png', -1),
               'down': load_image('down.png', 1),
               'finish': load_image('finish.png')}


class Camera:
    def __init__(self):
        self.dx = 0
        self.dy = 0

    def apply(self, obj):
        obj.rect.x = obj.origin_x + self.dx
        obj.rect.y = obj.origin_y + self.dy

    def update(self, target):
        self.dx = -(target.origin_x + target.rect.w // 2 + 150 - WIDTH // 2)
        self.dy = -(target.origin_y + target.rect.h // 2 - 50 - HEIGHT // 2)


def render(points, bike, camera):
    bike.update()
    angle_x, angle_y, angle_dif_size, angle_w, angle_h = 10, 60, 4, 100, 30
    angle_rect = pygame.Rect(angle_x + angle_dif_size // 2, angle_y + angle_dif_size // 2, angle_w, angle_h)
    angle_colors = {30: pygame.Color('green'),
                    50: pygame.Color('yellow'),
                    70: pygame.Color('orange'),
                    100: pygame.Color('red')}  # когда большой угол шкала красная, маленький - зеленая; всё в %
    screen.fill(pygame.Color('light blue'))
    tick = clock.tick(FPS)
    bike.origin_x += bike.speed // tick
    sprite_group.draw(screen)
    bike_group.draw(screen)
    camera.update(bike)
    for sprite in all_sprites:
        camera.apply(sprite)
    draw_text(['FPS: ' + str(int(1000 / tick))], 10, 560, 20, pygame.Color('black'))
    if not bike.crashed:  # когда он разбит интерфейса нет
        ########################   POINTS GUI
        intro_text = ["ОЧКИ: " + str(int(points))]
        draw_text(intro_text, 20, 10, 30, pygame.Color('black'))
        ########################   ANGLE GUI
        screen.fill(pygame.Color('gray'), (angle_x, angle_y, angle_w + angle_dif_size, angle_h + angle_dif_size))
        size = min(max((abs(bike.angle) - 4) * 100 // (bike.max_angle - 4), 0), 100)
        angle_rect.w = size
        col = None
        for i in angle_colors.keys():
            if size <= i:
                col = angle_colors[i]
                break
        screen.fill(col, angle_rect)
        draw_text(['УГОЛ'], angle_y + angle_h + 10, angle_x, 30, pygame.Color('dark gray'))
    ########################
    else:
        draw_text(['РАЗБИЛСЯ'], 200, 200, 50, pygame.Color('black'))
        draw_text(['РАЗБИЛСЯ'], 200 + 5, 200 + 5, 50, pygame.Color('white'))
        if bike.cur_frame == 3:
            bike.crash_finish()


class ScreenFrame(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.rect = (0, 0, 500, 500)


all_sprites = pygame.sprite.Group()
sprite_group = pygame.sprite.Group()
bike_group = pygame.sprite.Group()


class Sprite(pygame.sprite.Sprite):
    def __init__(self, group):
        super().__init__(group)
        self.rect = None
        self.origin_x = self.origin_y = None

    def get_event(self, event):
        pass


class Tile(Sprite):
    def __init__(self, tile_type, pos_x, pos_y):
        super().__init__((sprite_group, all_sprites))
        self.image = tile_images[tile_type]
        self.tile_type = tile_type
        self.rect = self.image.get_rect().move(tile_width * pos_x,
                                               tile_height * pos_y)
        self.origin_x = pos_x * tile_width
        self.origin_y = pos_y * tile_height
        self.mask = pygame.mask.from_surface(self.image)


class Bike(Sprite):
    def __init__(self, sheet, columns, rows, x, y):
        super().__init__((all_sprites, bike_group))
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x, y)
        self.origin_x = x
        self.origin_y = y
        self.angle = 0
        self.speed = 0
        self.origin_angle = 0
        self.a = 0
        self.g = 0
        self.angle_a = 0
        self.mask = pygame.mask.from_surface(self.image)
        self.crashed = False
        self.max_angle = 50
        self.max_speed = 220
        self.start_angling = False  # тут как с газом тормозом не работает, придется вот так
        self.finish = False

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, (sheet.get_width() - 129) // columns, sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(frame_location, self.rect.size)))
        for j in range(rows):
            for i in range(3):
                frame_location = (40 * columns + 43 * i, 48 * j)
                self.frames.append(sheet.subsurface(pygame.Rect(frame_location, (43, 48))))

    def update(self):
        if any([pygame.sprite.collide_mask(self, i) for i in sprite_group if i.tile_type == 'up']):
            self.angle = max(3, self.origin_angle)
            self.origin_angle = max(3, self.origin_angle)
            # print('up')
        elif any([pygame.sprite.collide_mask(self, i) for i in sprite_group if i.tile_type == 'down']):
            self.angle = min(-3, self.origin_angle)
            self.origin_angle = min(-3, self.origin_angle)
            # print('down')
        elif any([pygame.sprite.collide_mask(self, i) for i in sprite_group if i.tile_type == 'floor' or
                                                                             i.tile_type == 'brick']):
            self.angle = self.origin_angle
            # print('brick')

        if self.speed == 0 or self.start_angling:
            self.angle_to_zero()
        if not self.crashed:  # тут картинки обновляются, а если разбиты, то там не эти кадры должны быть
            if any([pygame.sprite.collide_mask(self, i) for i in sprite_group if i.tile_type == 'finish']):
                self.finish = True  # а еще когда разбился нельзя газовать и наклоняться так что скорость
            if self.angle >= 1:  # и угол наклона тоже сюда
                self.image = self.frames[min(self.angle, 4) + 1]
            elif self.angle == 0:
                index = self.frames.index(self.image)
                if index > 1:
                    self.image = self.frames[0]
                else:
                    if self.speed == 0:
                        self.image = self.frames[0]
                    else:
                        self.image = self.frames[1 - index]
            else:
                self.image = self.frames[5 - max(-3, self.angle)]
            if self.finish:
                self.speed = max(0, self.speed - 10)
                self.angle_to_zero()
            else:
                if self.a > 0:
                    bg_bike.play()
                elif self.a < 0:
                    if not_gas.get_num_channels() == 0:
                        not_gas.play()
                self.speed = max(0, min(self.speed + self.a, self.max_speed))
            self.origin_angle = self.origin_angle + self.angle_a
        else:
            if self.cur_frame < 3:
                self.image = self.frames[9 + int(self.cur_frame)]
                self.cur_frame += 0.1
            self.speed /= 1.1
        if not self.crashed and not any([pygame.sprite.collide_mask(self, i)
                    for i in sprite_group if i.tile_type != 'finish' and
                                             abs(i.rect.x - self.rect.x) < tile_width and
                                             abs(i.rect.y - self.rect.y) < tile_height and
                                             ((i.tile_type == 'brick' or i.tile_type == 'floor') and
                                              i.rect.y - tile_height < self.rect.y) or
                                             (i.tile_type == 'up' or i.tile_type == 'down')]):
            self.rect.top += self.g
            self.origin_y += self.g
            self.g += 1
        else:
            while any([pygame.sprite.collide_mask(self, i)
                       for i in sprite_group if i.tile_type != 'finish' and
                                                abs(i.rect.x - self.rect.x) < tile_width and
                                                abs(i.rect.y - self.rect.y) < tile_height and
                                                ((i.tile_type == 'brick' or i.tile_type == 'floor') and
                                                 i.rect.y - tile_height < self.rect.y) or
                                                (i.tile_type == 'up' or i.tile_type == 'down')]):
                self.rect.top -= 1
                self.origin_y -= 1
            self.g = 0
        if abs(self.origin_angle) >= self.max_angle and not self.crashed:
            self.crash()
        self.mask = pygame.mask.from_surface(self.image)

    def add_angle(self):
        if self.crashed:
            return
        self.start_angling = False
        if self.speed != 0:
            self.angle_a = 1

    def sub_angle(self):
        if self.crashed:
            return
        self.start_angling = False
        if self.speed != 0:
            self.angle_a = -1

    def gas(self):
        if self.crashed:
            return
        self.a = 2
        gas.play()

    def brake(self):
        if self.crashed:
            return
        self.a = -4

    def angle_to_zero(self):
        if self.crashed:
            return
        if self.origin_angle < 0:
            self.angle_a = 1
        elif self.origin_angle > 0:
            self.angle_a = -1
        else:
            self.angle_a = 0

    def crash(self):
        if self.crashed:
            return
        bg_bike.stop()
        gas.stop()
        not_gas.play()
        self.crashed = True

    def get_image_for_crash(self, i):  # i - это кадр от 0 до 3
        self.image = self.frames[9 + i]
        self.mask = pygame.mask.from_surface(self.image)

    def crash_finish(self):
        self.speed = 0
        self.max_speed = 0
        self.max_angle = 0
        self.origin_angle = 0
        self.angle = 0
        self.a = 0
        self.g = 0
        self.angle_a = 0


def draw_text(text, text_coord_y, text_coord_x, size_font, color):
    font = pygame.font.Font(None, size_font)
    for line in text:
        string_rendered = font.render(line, 1, color)
        _rect = string_rendered.get_rect()
        text_coord_y += 10
        _rect.top = text_coord_y
        _rect.x = text_coord_x
        text_coord_y += _rect.height
        screen.blit(string_rendered, _rect)


def start_screen():
    intro_text = ["Для продолжения нажмите любую клавишу"]
    fon = pygame.transform.scale(load_image('fon.jpg'), (WIDTH, HEIGHT))
    screen.blit(fon, (0, 0))
    pygame.draw.rect(screen, pygame.Color('white'), (50, 310, 500, 50))
    draw_text(intro_text, 320, 80, 30, pygame.Color('black'))
    while True:
        bg_music.play()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return  # начинаем игру
        pygame.display.flip()
        clock.tick(FPS)


def menu():
    global your_levels, your_record
    image = 'fon.jpg'
    global compl_game
    if compl_game:
        image = 'fon_perfect.jpg'  # при прохождении всех уровней меняется картинка
    fon = pygame.transform.scale(load_image(image), (WIDTH, HEIGHT))
    rects = []
    rect_side_x = 400
    rect_side_y = 100
    rect_offset = 100
    text_font = 60  # кнопки (rect, 0 - достижения 1 - играть, наведена мышь на кнопку или нет)
    for i in range(2):  # так можно понять в какой цвет например красить
        rects.append((pygame.Rect(rect_offset,
                                  rect_offset * (i + 1) + rect_side_y * i,
                                  rect_side_x, rect_side_y), i, False))
    while True:
        bg_music.play()
        screen.blit(fon, (0, 0))
        draw_text(['Меню'], 20, WIDTH // 2 - 300, 100, pygame.Color('white'))
        for _ in range(len(rects)):
            i, j, k = rects[_]  # rect, int
            if j == 0:
                if k:
                    screen.fill(pygame.Color('black'), i)
                    draw_text(['Достижения'], i.y + i.h // 2 - text_font // 2,
                              i.x + i.w * 0.3,
                              text_font, pygame.Color('white'))
                else:
                    screen.fill(pygame.Color('orange'), i)
                    draw_text(['Достижения'], i.y + i.h // 2 - text_font // 2,
                              i.x + i.w * 0.3,
                              text_font, pygame.Color('black'))
            elif j == 1:
                if k:
                    screen.fill(pygame.Color('black'), i)
                    draw_text(['Играть'], i.y + i.h // 2 - text_font // 2,
                              i.x + i.w * 0.3,
                              text_font, pygame.Color('white'))
                else:
                    screen.fill(pygame.Color('white'), i)
                    draw_text(['Играть'], i.y + i.h // 2 - text_font // 2,
                              i.x + i.w * 0.3,
                              text_font, pygame.Color('black'))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i in range(len(rects)):
                    rectt, j, _ = rects[i]
                    if click_rect(event.pos, rectt):
                        return j  # 0 - достижения 1 - играть
            elif event.type == pygame.MOUSEMOTION:
                for i in range(len(rects)):
                    rectt, j, k = rects[i]
                    if click_rect(event.pos, rectt):
                        rects[i] = (rectt, j, True)
                    else:
                        rects[i] = (rectt, j, False)
        pygame.display.flip()
        clock.tick(FPS)


def achievements():
    global your_levels, your_record
    text = ['Максимум очков: ' + str(your_record), '',  # пустая строка для интервала между
            'Пройдены уровни: ' + str(your_levels), '',
            'Если пройти все уровни,', 'поменяется фоновый рисунок!',
            'Нажмите любую кнопку для продолжения']
    fon = pygame.transform.scale(load_image('fon_pause.jpg'), (WIDTH, HEIGHT))
    while True:
        bg_music.play()
        screen.blit(fon, (0, 0))
        draw_text(['Достижения'], 50, WIDTH // 2 - 200, 100, pygame.Color('white'))
        draw_text(text, 150, 20, 40, pygame.Color('white'))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.KEYDOWN:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return
        pygame.display.flip()
        clock.tick(FPS)


def controls():
    intro_text = ["Управление", "",
                  "w - газ, s - тормоз",
                  "a/d - наклон",
                  "Не наклоняйтесь",
                  "слишком сильно,",
                  "иначе упадёте",
                  "с мотоцикла!",
                  "Когда шкала наклона",
                  "хоть чуть-чуть заполняется,",
                  "начисляются очки",
                  "p - пауза"]
    fon = pygame.transform.scale(load_image('fon2.jpg'), (WIDTH, HEIGHT))
    screen.blit(fon, (0, 0))
    pygame.draw.rect(screen, pygame.Color('white'), (10, 50, 300, 400))
    draw_text(intro_text, 50, 20, 30, pygame.Color('black'))
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return  # начинаем игру
        pygame.display.flip()
        clock.tick(FPS)


def pause():
    text = ['Управление - [C]',
            'Продолжить - любая клавиша или нажатие мыши']
    fon = pygame.transform.scale(load_image('fon_pause.jpg'), (WIDTH, HEIGHT))
    while True:
        screen.blit(fon, (0, 0))
        draw_text(['ПАУЗА'], 50, WIDTH // 2 - 100, 100, pygame.Color('white'))
        draw_text(text, 200, 50, 30, pygame.Color('white'))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    controls()
                else:
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return
        pygame.display.flip()
        clock.tick(FPS)


def load_level(filename):
    filename = "data/levels/" + filename
    with open(filename, 'r') as mapFile:
        level_map = [line.strip() for line in mapFile]
    max_width = max(map(len, level_map))
    return list(map(lambda x: x.ljust(max_width, '.'), level_map))


def generate_level(level):
    xx, yy = None, None
    for y in range(len(level)):
        for x in range(len(level[y])):
            if level[y][x] == '#':
                Tile('floor', x, y)
            elif level[y][x] == '$':
                Tile('brick', x, y)
            elif level[y][x] == '<':
                Tile('up', x, y)
            elif level[y][x] == '>':
                Tile('down', x, y)
            elif level[y][x] == '@':
                xx, yy = x, y
            elif level[y][x] == '%':
                for i in range(y + 1):
                    Tile('finish', x, i)
    return xx, yy


def start_level(a):
    left = 200
    text = ['Уровень ' + str(a)]
    lvl_start.play()
    for i in range(100):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
        screen.fill(pygame.Color('white'))
        num = HEIGHT / tile_height + 1
        if num % 1:
            num = int(num) + 1
        for j in range(num):
            y_offset = (i * 3) % tile_height
            min_y = (j - 1) * tile_height
            mid_y = min_y + tile_height // 2 + y_offset
            mid_x = left + tile_width // 2
            pygame.draw.polygon(screen, pygame.Color('blue'), ((left, mid_y),
                                                               (mid_x, min_y + y_offset),
                                                               (left + tile_width, mid_y),
                                                               (mid_x, min_y + y_offset + tile_height)))
        draw_text(text, 50 - i // 2, 10, 100, pygame.Color('black'))
        clock.tick(FPS)
        pygame.display.flip()


def level(level):
    start_level(level)
    xx, yy = generate_level(load_level('l' + str(level)))
    bike = Bike(load_image('red_bike.png', -1), 9, 1, xx * tile_width, yy * tile_height)
    camera = Camera()
    points = 0
    sound_played = False
    finish_frame = 0  # надпись разбился или пройден уровень держится пару секунд
    global your_record
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    pause()  # на каждую клавишу двжение
                if event.key == pygame.K_a:  # причем если менять физ. переменную
                    bike.add_angle()  # скорость наклон и т д напрямую
                if event.key == pygame.K_d:  # надо будет нажимать клавишу несколько раз
                    bike.sub_angle()  # а если сделать так что она меняется независимо от
                if event.key == pygame.K_w:  # w вроде нажата и не отжата = разгон через функцию
                    bike.gas()  # она вызывается 1 раз но разгон постоянно...
                if event.key == pygame.K_s:  # нажатий, то можно зажимать клавишу, как в норм играх
                    bike.brake()
                    bike.brake()
                    bike.sub_angle()
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_w:  # ...пока не отжата
                    bike.brake()
                if event.key == pygame.K_a or \
                        event.key == pygame.K_d:
                    bike.start_angling = True
        if abs(bike.angle) >= 45:
            points += 1
        elif abs(bike.angle) >= 30:
            points += 0.3
        elif abs(bike.angle) >= 10:
            points += 0.2
        elif abs(bike.angle) >= 4:
            points += 0.1
        render(points, bike, camera)
        if bike.crashed:
            finish_frame += 1
            if finish_frame >= FPS * 4:
                for i in all_sprites:
                    i.kill()
                for i in sprite_group:
                    i.kill()
                for i in bike_group:
                    i.kill()
                return False
        if bike.finish and bike.speed == 0:
            if finish_frame <= FPS * 4:
                if points >= 300:
                    if not sound_played:
                        sound_played = True
                        win.play()
                    draw_text(['УРОВЕНЬ ' + str(level) + ' ПРОЙДЕН!'], 200, 100, 50, pygame.Color('white'))
                else:
                    draw_text(['НЕДОСТАТОЧНО ОЧКОВ!'], 200, 100, 50, pygame.Color('white'))
                finish_frame += 1
            else:
                for i in all_sprites:
                    i.kill()
                for i in sprite_group:
                    i.kill()
                for i in bike_group:
                    i.kill()
                if int(points) > your_record:  # обновление сохранения
                    your_record = int(points)
                return points >= 300
        pygame.display.flip()


def choose_level():
    fon = pygame.transform.scale(load_image('fon_pause.jpg'), (WIDTH, HEIGHT))
    rects = []
    rect_side = 100
    rect_offset = 50
    text_font = 60  # кнопки уровня и если не дошел еще до уровня то 2 значение False
    for i in range(levels_amount):  # так можно понять в какой цвет например красить
        rects.append((pygame.Rect(rect_offset + i * (rect_side + rect_offset),
                                  rect_offset * 3, rect_side, rect_side), your_levels >= i))
    while True:
        screen.blit(fon, (0, 0))
        draw_text(['Выбор уровня'], 20, WIDTH // 2 - 300, 100, pygame.Color('white'))
        for k in range(len(rects)):
            i, j = rects[k]  # rect, boolean
            if j:
                screen.fill(pygame.Color('green'), i)
                draw_text([str(k + 1)], i.y + i.h // 2 - text_font // 2,
                          i.x + i.w * 0.3,
                          text_font, pygame.Color('black'))
            else:
                screen.fill(pygame.Color('red'), i)
                draw_text(['Х'], i.y + i.h // 2 - text_font // 2,
                          i.x + i.w * 0.3,
                          text_font, pygame.Color('black'))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for i in range(len(rects)):
                    rectt, j = rects[i]  # j - дошел до уровня или нет
                    if click_rect(event.pos, rectt) and j:
                        return i
        pygame.display.flip()
        clock.tick(FPS)


def game(levels, current_level=None):
    global your_levels
    start_screen()
    action = menu()  # 0 - достижения 1 - играть
    while action == 0:
        achievements()
        action = menu()
    current_level = choose_level()  # счёт с 0, так удобно
    if current_level == 0:
        controls()
    game_completed = False
    while current_level < levels:
        if not level(current_level + 1):
            game_completed = False
            start_screen()
            controls()
        else:
            game_completed = True
            current_level += 1
            if your_levels < current_level:  # сохранение обновляется
                your_levels = current_level
    return game_completed


def finish_game():
    fon = pygame.transform.scale(load_image('finish_game.jpg'), (WIDTH, HEIGHT))
    global your_record
    text = ['Рекорд сессии: ' + str(your_record), 'Прошлый рекорд: ' + str(prev_record),
            'Нажмите любую клавишу, чтобы продолжить']
    while True:
        screen.blit(fon, (0, 0))
        draw_text(['ПРОЙДЕНО'], 50, 20, 100, pygame.Color('white'))
        draw_text(text, 200, 50, 30, pygame.Color('black'))
        draw_text(text, 200, 52, 30, pygame.Color('white'))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
                return
            elif event.type == pygame.KEYDOWN:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                return
        pygame.display.flip()
        clock.tick(FPS)


while not game(levels_amount):
    pass
if not compl_game:
    compl_game = True
    finish_game()
with open('data/save.txt', 'w') as f:
    f.write(f'''level={your_levels}
max_points={your_record}
game_completed={compl_game}''')
pygame.quit()
