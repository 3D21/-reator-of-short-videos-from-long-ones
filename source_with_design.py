import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess
import cv2
import requests
from bs4 import BeautifulSoup
import re
from pytube import YouTube
from tkinter import ttk
from moviepy.video.io.VideoFileClip import VideoFileClip
import os
import threading
import pyglet
pyglet.font.add_file('clacon2.ttf')
pyglet.font.add_file('10mal12Lampen.ttf')

stopping_cutting_video_flag = 0  # 1 - если нажата кнопка "Остановить нарезку видео"
stopped_function_name_flag = ""  # Нужно для запуска режима, который был остановлен кнопкой "Остановить нарезку видео"
segments_times = []              # Хранит таймкоды для нарезки
selected_segment_time = 0        # Выбирается пользователем в программе, означает желаемую длительность короткого видео
project_name = ""                # Название проекта
video_path = ""                  # Хранит путь до видео, которое будет обрабатываться
output_folder = f"C:/Video_Cutter_Files/{project_name}"
# Создание папки, если она не существует
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print("Путь успешно создан")


def convert_timecode_to_hhmmss_format(timecode):
    parts = timecode.split(':')

    if len(parts) == 2:  # Форматы M:SS и MM:SS
        minutes, seconds = parts
        hours = 0
    elif len(parts) == 3:  # Формат H:MM:SS
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Неправильный формат таймкода: {timecode}")

    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def extract_timecodes_from_file(file_path, video_duration):
    time_intervals = []
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for i, line in enumerate(lines):
            timecode, name = line.strip().split(' ', 1)
            timecode = convert_timecode_to_hhmmss_format(timecode)
            name = name.replace("/", "").replace("\\", "").replace(":", "").replace("*", "").replace("?", "").replace(
                "<", "").replace(">", "").replace("|", "").replace("–", "").replace("`", "").replace("\'", "").replace(
                "′", "").replace(
                ".", "").replace("«", "").replace("»", "").replace("[", "").replace("]", "").replace(";", "").replace(
                "=", "").replace(",", "").replace("#", "").replace("%", "").replace("&", "").replace("+", "").replace(
                "@", "").replace("", "")

            start_time = timecode
            if i < len(lines) - 1:
                end_time = convert_timecode_to_hhmmss_format(lines[i + 1].split(' ', 1)[0])
            else:
                hours_temp = int(video_duration // 3600)
                minutes_temp = int((video_duration % 3600) // 60)
                seconds_temp = int(video_duration % 60)
                end_time = f"{hours_temp:02d}:{minutes_temp:02d}:{seconds_temp:02d}"  # Для последнего видео начало и конец совпадают

            time_intervals.append([start_time, end_time, name])

    return time_intervals


def get_video_duration_from_url(video_url):
    yt = YouTube(video_url)
    duration = yt.length
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02d}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))


def get_timecodes_from_url(url):
    response = requests.get(url)
    # Создаем объект BeautifulSoup для парсинга HTML-кода ответа
    text = str(BeautifulSoup(response.text, 'html.parser'))
    names = []
    times = []

    names_final = []
    times_final = []

    # Используем регулярное выражение для поиска и извлечения данных
    pattern = r'{"title":{"simpleText":"([^"]+)"},"timeDescription":{"simpleText":"([^"]+)"}'
    matches = re.findall(pattern, text)

    # Извлекаем и сохраняем данные в соответствующие массивы
    for match in matches:
        name, time = match
        names.append(name)
        times.append(time)

    for x in names:  # Здесь сортируем, чтобы не было повторяющихся элементов
        if x not in names_final:
            names_final.append(x)
    for x in times:  # Здесь тоже сортируем, чтобы не было повторяющихся элементов
        if x not in times_final:
            times_final.append(x)

    segments_times.clear()

    for i in range(len(times_final)):
        # Получаем начальное время отрезка (текущий элемент в times_final)
        start_time = times_final[i]
        if len(start_time) == 5:
            start_time = "00:" + start_time
        elif len(start_time) == 4:
            start_time = "00:0" + start_time
        elif len(start_time) == 7:
            start_time = "0" + start_time
        # Получаем конечное время отрезка (следующий элемент в times_final, если он есть, иначе берем длительность видео)
        end_time = times_final[i + 1] if i + 1 < len(times_final) else get_video_duration_from_url(url)
        if len(end_time) == 5:
            end_time = "00:" + end_time
        elif len(end_time) == 4:
            end_time = "00:0" + end_time
        elif len(end_time) == 7:
            end_time = "0" + end_time
        # Получаем название отрезка (текущий элемент в names_final)
        segment_name = names_final[i]

        # Добавляем информацию об отрезке в список segments
        segments_times.append([start_time, end_time, segment_name])
    return segments_times


def video_play(path):
    subprocess.run(subprocess.run(['start', '', path], shell=True))


def select_file():
    global video_path
    video_path = filedialog.askopenfilename(title="Выберете .mp4 файл", filetypes=[("MP4 files", "*.mp4")])
    file_name = ""
    if len(video_path) > 32:
        file_name = "...{}".format(video_path[-32:])

    video_label.config(text=f"Выбранный файл: {file_name}", fg="#84ffc9")
    global cap
    cap = cv2.VideoCapture(video_path)
    # Превью для видео
    video_preview = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    # Переходим к 5-й секунде видео
    cap.set(cv2.CAP_PROP_POS_MSEC, 5000)
    # Читаем кадр
    ret, frame = cap.read()
    # Преобразуем кадр в изображение
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    image = image.resize((300, 200))
    photo = ImageTk.PhotoImage(image)
    canvas_video.create_image(0, 0, anchor="nw", image=photo)
    canvas_video.photo = photo  # сохраняем ссылку на изображение
    play_button = tk.Button(text="Воспроизвести", font=('Classic Console Neue',10),bg=button_bg_color, command=lambda: video_play(video_path))
    canvas_video.create_window(150, 100, window=play_button, width=100, height=20)


def select_segment_time_in_seconds():
    def get_number(time):
        global selected_segment_time
        selected_segment_time = time
        segment_time_label.config(text=f"Время одного сегмента --> {selected_segment_time} секунд", fg="#84ffc9")
        print(selected_segment_time)

    content_window = tk.Toplevel(window)
    content_window.title("Укажите время одного сегмента")
    content_window.configure(bg="#2ec4b6")
    # content_window.geometry("400x200")
    content_window_width = 400
    content_window_height = 200
    center_window(content_window, content_window_width, content_window_height)
    entry = tk.Entry(content_window, width=40, font=('Classic Console Neue', 11), fg="#011627")
    entry.insert(0, selected_segment_time)
    entry.pack(pady=(10, 10))
    entry.pack()
    save_button = tk.Button(content_window, text="Ок", font=('Classic Console Neue', 11),
                            command=lambda: get_number(entry.get()))
    save_button.pack()


def select_project_name():
    def get_name(name):
        global project_name
        project_name = name
        project_name_label.config(text=f"Название проекта --> {project_name}", fg="#84ffc9")
        saved_label.config(text="Сохранено!", font=('Classic Console Neue', 12), fg="#156064")
        print(project_name)

    content_window = tk.Toplevel(window)
    content_window.configure(bg="#2ec4b6")
    content_window.title("Укажите имя проекта")
    # content_window.geometry("400x200")
    content_window_width = 425
    content_window_height = 200
    center_window(content_window, content_window_width, content_window_height)
    entry = tk.Entry(content_window, width=50, font=('Classic Console Neue', 11), fg="#011627")
    entry.insert(0, project_name)
    entry.pack(pady=(10, 0))
    save_button = tk.Button(content_window, text="Ок",font=('Classic Console Neue', 11),
                            command=lambda: get_name(entry.get()))
    info_label = tk.Label(content_window,
                          text="Если путь для сохранения с таким именем существует,\nи там находятся уже сохранённые таймкоды -\nто они могут загрузиться автоматически", bg = "#2ec4b6",font=('Classic Console Neue', 11),
                          fg="blue", justify="center")
    info_label.pack(pady=(10, 0))
    saved_label = tk.Label(content_window, text="",bg="#2ec4b6", fg="#84ffc9", justify="center")
    saved_label.pack(pady=(10, 0))
    save_button.pack()


def select_savepath():
    folder_path = filedialog.askdirectory(title="Выберите папку")

    if folder_path:
        global output_folder
        output_folder = f"{folder_path}/{project_name}"
        savepath_label.config(text=f"Путь для сохранения файлов -->{output_folder[:19]}...", fg="#84ffc9")
        print(output_folder)

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print("Путь успешно создан")
    timecodes_file_path = os.path.join(output_folder, "saved_timecodes.txt")
    if os.path.exists(timecodes_file_path):
        global segments_times
        segments_times = extract_timecodes_from_file(timecodes_file_path, 3600)
        print("Таймкоды извлечены:", segments_times)


def create_timecodes():
    def button_get_timecodes_from_url(url_link):
        try:
            global segments_times
            segments_times = get_timecodes_from_url(url_link)

            sanitized_segments = []
            for segment in segments_times:
                start_time, end_time, name = segment
                sanitized_name = name.replace("/", "").replace("\\", "").replace(":", "").replace("*", "").replace("?",
                                                                                                                   "").replace(
                    "<", "").replace(">", "").replace("|", "").replace("–", "").replace("`", "").replace("\'",
                                                                                                         "").replace(
                    "′", "").replace(
                    ".", "").replace("«", "").replace("»", "").replace("[", "").replace("]", "").replace(";",
                                                                                                         "").replace(
                    "=", "").replace(",", "").replace("#", "").replace("%", "").replace("&", "").replace("+",
                                                                                                         "").replace(
                    "@", "").replace("", "")
                sanitized_segments.append([start_time, end_time, sanitized_name])

            segments_times = sanitized_segments

            if len(segments_times) > 0:
                save_timecodes_to_file(segments_times, output_folder)
                saved_label.config(text="Успешно! Можете закрывать окно", font=('Classic Console Neue', 11),bg="#2ec4b6", fg="#156064")
                global timecodes_existance_flag
                timecodes_existance_flag = True
            else:
                saved_label.config(text="Не получилось создать таймкоды! Попробуйте снова", font=('Classic Console Neue', 11),bg="#2ec4b6", fg="red")
        except:
            saved_label.config(text="Возникла ошибка! Попробуйте снова", font=('Classic Console Neue', 11),bg="#2ec4b6", fg="#E40046")

    url = ""
    content_window = tk.Toplevel(window)
    content_window.title("Вставьте ссылку на видео")
    content_window.configure(bg="#2ec4b6")
    # content_window.geometry("400x200")
    content_window_width = 400
    content_window_height = 200
    center_window(content_window, content_window_width, content_window_height)
    entry = tk.Entry(content_window, width=40, font=('Classic Console Neue', 11), fg="#011627")
    entry.insert(0, url)
    entry.pack(pady=(10,10))

    # Добавление метки "Сохранено!"
    global saved_label
    saved_label = tk.Label(content_window, text="Нажмите кнопку и ожидайте!",font=('Classic Console Neue', 11),bg="#2ec4b6", fg="blue")
    saved_label.pack(pady=(0,10))

    save_button = tk.Button(content_window, text="Ок",font=('Classic Console Neue', 11),
                            command=lambda: button_get_timecodes_from_url(entry.get()))
    save_button.pack()


def save_timecodes_to_file(segment_times, output_folder):
    # Путь к файлу, в который будут записаны таймкоды
    output_file_path = os.path.join(output_folder, "saved_timecodes.txt")

    # Открываем файл для записи
    with open(output_file_path, 'w', encoding='utf-8') as file:
        for segment in segment_times:
            # Извлекаем первый и третий элемент из каждого подмассива
            start_time = segment[0]
            description = segment[2]
            # Формируем строку и записываем ее в файл
            file.write(f"{start_time} {description}\n")


def open_timecodes_table():
    def delete_timecode():
        try:
            global segments_times

            global var_row_to_delete
            print(var_row_to_delete)
            del segments_times[var_row_to_delete]
            update_table(segments_times)
            for x in segments_times:
                print(x)
        except:
            show_error_message("Выберете таймкод, который нужно удалить!!!")
            return

    def add_timecode():
        global segments_times
        segments_times.append(["00:00:00", "00:00:00", "Введите название"])
        update_table(segments_times)

    def show_error_message(message):
        error_window = tk.Toplevel(table_window)
        error_window.title("ОШИБКА")
        error_window.geometry("500x100")  # Установка размера окна
        label = tk.Label(error_window, text=message)
        label.pack()

    def save_changes(row, col, new_value):

        if col == 1:  # Номер таймкода не редактируется
            return

        if col in [2, 3]:  # Проверка для столбцов с временем
            try:
                hours, minutes, seconds = map(int, new_value.split(':'))
                if hours > 24 or minutes > 59 or seconds > 59:
                    show_error_message(
                        "Неверный формат времени. Проверьте правильность значений часов, минут или секунд")
                    return
                new_value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"  # Приведение к формату ЧЧ:ММ:СС
            except ValueError:
                show_error_message("Неверный формат времени. Используйте формат ЧЧ:ММ:СС")
                return

        segments_times[row - 1][col - 2] = new_value
        update_table(segments_times)
        saved_label.config(text="Сохранено!")  # Обновление текста метки
        for interval in segments_times:
            print(interval)

    def select_file():
        global video_path
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        temporary_duration = 3600
        if video_path:
            with VideoFileClip(video_path) as video:
                temporary_duration = video.duration
        if file_path:
            global segments_times
            segments_times = extract_timecodes_from_file(file_path,
                                                         temporary_duration)  # Здесь предполагается, что длительность видео 3600 секунд, если не выбрано видео
            update_table(segments_times)

    def update_table(time_intervals):
        table.delete(*table.get_children())
        for i, interval in enumerate(time_intervals, start=1):
            table.insert('', 'end', values=[i] + interval)
        if len(time_intervals) > 0:
            global timecodes_existance_flag
            timecodes_existance_flag = True

    def show_cell_content(event):
        item = table.identify('item', event.x, event.y)
        column = table.identify('column', event.x, event.y)
        if item and column:
            row = table.index(item) + 1
            col = int(column.split('#')[-1])
            print(f"Double click at row {row}, column {col}")
            if col == 1:  # Номер таймкода не редактируется
                return
            value = table.item(item)['values'][col - 1]
            content_window = tk.Toplevel(table_window)
            content_window.title("Редактирование содержимого")
            content_window.geometry("400x200")
            entry = tk.Entry(content_window, width=50)
            entry.insert(0, value)
            entry.pack()

            # Добавление метки "Сохранено!"
            global saved_label
            saved_label = tk.Label(content_window, text="", fg="green")
            saved_label.pack()

            save_button = tk.Button(content_window, text="Сохранить",
                                    command=lambda: save_changes(row, col, entry.get()))
            save_button.pack()

    def paste_timecodes():
        def create_file_with_content(file_path, content):
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f"Файл {file_path} успешно создан и записан.")
                return file_path
            except Exception as e:
                print(f"Произошла ошибка при создании или записи файла: {e}")
                return None

        def delete_file(file_path):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Файл {file_path} успешно удален.")
                    return True
                else:
                    print(f"Файл {file_path} не найден.")
                    return False
            except Exception as e:
                print(f"Произошла ошибка при удалении файла: {e}")
                return False

        def get_timecodes_from_text(timecodes_text):
            global video_path
            temporary_duration = 3600
            temporary_path_of_timecodes_text = create_file_with_content("C:/Video_Cutter_Files/temporary_timecodes.txt",
                                                                        timecodes_text)
            if video_path:
                with VideoFileClip(video_path) as video:
                    temporary_duration = video.duration
            try:
                global segments_times
                segments_times = extract_timecodes_from_file(temporary_path_of_timecodes_text, temporary_duration)

                if len(segments_times) > 0:
                    save_timecodes_to_file(segments_times, output_folder)
                    saved_label.config(text="Успешно! Можете закрывать окно", fg="green")
                    global timecodes_existance_flag
                    timecodes_existance_flag = True

                else:
                    saved_label.config(text="Не получилось создать таймкоды! Попробуйте снова", fg="red")
                delete_file(temporary_path_of_timecodes_text)
                update_table(segments_times)
            except:
                saved_label.config(text="Возникла ошибка! Попробуйте снова", fg="red")

        url = ""
        content_window = tk.Toplevel(window)
        content_window.title("Вставьте таймкоды из Ютуба")
        # content_window.geometry("400x200")
        content_window_width = 800
        content_window_height = 400
        center_window(content_window, content_window_width, content_window_height)
        text_input = tk.Text(content_window, width=80, height=20,wrap="none")
        text_input.pack(pady=10)

        # Добавление метки "Сохранено!"
        global saved_label
        saved_label = tk.Label(content_window, text="Нажмите кнопку и ожидайте!", fg="blue")
        saved_label.pack()

        save_button = tk.Button(content_window, text="Ок",
                                command=lambda: get_timecodes_from_text(text_input.get("1.0", tk.END)))
        save_button.pack()

    table_window = tk.Tk()
    table_window.title("Таблица временных интервалов")
    table_window_width = 1000
    table_window_height = 300
    center_window(table_window, table_window_width, table_window_height)

    table = ttk.Treeview(table_window, columns=("Number", "Start Time", "End Time", "Name"), show="headings")
    table.heading("Number", text="Номер №")
    table.heading("Start Time", text="Начало")
    table.heading("End Time", text="Конец")
    table.heading("Name", text="Имя")
    table.pack(fill="both", expand=True)
    var_row_to_delete = 0

    def row_recognition(event):
        global var_row_to_delete
        item = table.identify('item', event.x, event.y)
        row = table.index(item)
        var_row_to_delete = row
        print(row)

    table.bind("<Button-1>", row_recognition)
    table.bind("<Double-Button-1>", show_cell_content)
    update_table(segments_times)
    select_button = tk.Button(table_window, text="Выбрать файл", command=select_file)
    select_button.pack(side="left", padx=5)

    add_button = tk.Button(table_window, text="Добавить таймкод", command=add_timecode)
    add_button.pack(side="left", padx=5)

    delete_button = tk.Button(table_window, text="Удалить таймкод", command=delete_timecode)
    delete_button.pack(side="left", padx=5)

    save_button = tk.Button(table_window, text="Сохранить в файл",
                            command=lambda: save_timecodes_to_file(segments_times, output_folder))
    save_button.pack(side="left", padx=5)

    paste_button = tk.Button(table_window, text="Вставить таймкоды из Ютуба", command=paste_timecodes)
    paste_button.pack(side="left", padx=5)

    table_window.mainloop()


def convert_time_to_seconds(time_str):
    # Разбиваем строку на часы, минуты и секунды.
    hours, minutes, seconds = map(int, time_str.split(':'))

    # Вычисляем общее количество секунд
    total_seconds = hours * 3600 + minutes * 60 + seconds

    return total_seconds


def cut_video(input_video, output_video, start_time, end_time):
    # Загружаем видео
    video = VideoFileClip(input_video)

    # Вырезаем кусок видео
    clipped_video = video.subclip(start_time, end_time)

    # Сохраняем вырезанный кусок видео
    clipped_video.write_videofile(output_video, codec="libx264")

    # Освобождаем ресурсы
    video.close()
    clipped_video.close()


def cut_and_segment_video_by_timecodes(input_video, segments_times, output_folder, segment_duration):
    global stopped_function_name_flag
    try:
        start_progressbar()
        video = VideoFileClip(input_video)
        time_intervals = segments_times

        for interval in time_intervals:
            if stopping_cutting_video_flag:
                global stopped_function_name_flag
                stopped_function_name_flag = "cut_and_segment_video_by_timecodes"
                break
            start_time = convert_time_to_seconds(interval[0])
            end_time = convert_time_to_seconds(interval[1])
            video_name = interval[2]

            # Создаем папку для сохранения сегментов текущего интервала
            interval_output_folder = os.path.join(output_folder, "by_custom_timecodes", video_name)
            os.makedirs(interval_output_folder, exist_ok=True)

            # Рассчитываем общее количество сегментов для текущего временного интервала
            interval_duration = end_time - start_time
            # Вычисляем количество сегментов, которые нужно создать
            num_segments = int(interval_duration // segment_duration)
            if interval_duration % segment_duration != 0:
                num_segments += 1
            # Рассчитываем длительность каждого сегмента в текущем интервале
            segment_duration_exact = interval_duration / num_segments

            # Нарезаем видео на сегменты в текущем интервале
            for j in range(num_segments):
                if stopping_cutting_video_flag:

                    stopped_function_name_flag = "cut_and_segment_video_by_timecodes"
                    break
                segment_start_time = start_time + j * segment_duration_exact
                segment_end_time = min(start_time + (j + 1) * segment_duration_exact, end_time)

                segment_output_path = os.path.join(interval_output_folder, f"{j + 1}_{video_name}.mp4")
                if os.path.exists(segment_output_path):
                    continue  # Если файл уже существует, переходим к следующей итерации
                cut_video(input_video, segment_output_path, segment_start_time, segment_end_time)
                output_of_result.insert(tk.END, f"{segment_output_path}\n")
        video.close()
        stop_progressbar()
    except:
        output_of_result.insert(tk.END,
                                "Проверьте правильность введённых данных, обработка видео столкнулась с ошибками\n")
        stop_progressbar()


def cut_video_by_timecodes(input_video, segments_times, output_folder):
    global stopped_function_name_flag
    try:
        start_progressbar()
        video = VideoFileClip(input_video)
        total_duration = video.duration
        time_intervals = segments_times

        for interval in time_intervals:

            if stopping_cutting_video_flag:

                stopped_function_name_flag = "cut_video_by_timecodes"
                break

            start_time = convert_time_to_seconds(interval[0])
            if len(interval) > 1:
                end_time = convert_time_to_seconds(interval[1])
            else:
                end_time = total_duration

            output_folder_by_timecodes = os.path.join(output_folder, "by_timecodes")
            output_video = os.path.join(output_folder_by_timecodes,
                                        f"{interval[2]}.mp4")  # Формируем путь к выходному видео
            os.makedirs(output_folder_by_timecodes, exist_ok=True)  # Создаем папку "by_timecodes", если её нет

            if os.path.exists(output_video):
                continue  # Если файл уже существует, переходим к следующей итерации

            cut_video(input_video, output_video, start_time, end_time)
            output_of_result.insert(tk.END, f"{output_video}\n")

        video.close()
        stop_progressbar()
    except:
        output_of_result.insert(tk.END,
                                "Проверьте правильность введённых данных, обработка видео столкнулась с ошибками\n")
        stop_progressbar()


def cut_video_by_segments(input_video, output_folder, segment_duration):
    global stopped_function_name_flag
    try:
        start_progressbar()
        video = VideoFileClip(input_video)
        total_duration = video.duration

        # Вычисляем количество сегментов
        num_segments = int(total_duration / segment_duration)
        if total_duration % segment_duration != 0:
            num_segments += 1

        # Нарезаем видео на сегменты
        for i in range(num_segments):

            if stopping_cutting_video_flag:

                stopped_function_name_flag = "cut_video_by_segments"
                break

            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)

            # Формируем путь к выходному видео
            output_folder_by_timecodes = os.path.join(output_folder, "by_segments")
            output_video = os.path.join(output_folder_by_timecodes, f"segment_{i + 1}.mp4")
            os.makedirs(output_folder_by_timecodes, exist_ok=True)

            if os.path.exists(output_video):
                continue  # Если файл уже существует, переходим к следующей итерации

            # Вырезаем кусок видео
            cut_video(input_video, output_video, start_time, end_time)

            output_of_result.insert(tk.END, f"{output_video}\n")
        # Освобождаем ресурсы
        video.close()
        stop_progressbar()
    except:
        output_of_result.insert(tk.END,
                                "Проверьте правильность введённых данных, обработка видео столкнулась с ошибками\n")
        stop_progressbar()


def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def start_processing(func, *args, **kwargs):
    # Запуск переданной функции в отдельном потоке
    output_of_result.insert(tk.END, "Пошла загрузка\n")
    processing_thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    processing_thread.start()


def update_button_state(flag, action_button):
    if flag and timecodes_existance_flag:
        action_button.config(state=tk.NORMAL)
    else:
        action_button.config(state=tk.DISABLED)

def uptade_stop_flag():
    global stopping_cutting_video_flag

    if stopping_cutting_video_flag:
        stopping_cutting_video_flag=0
        if stopped_function_name_flag == "cut_video_by_segments":
            start_processing(cut_video_by_segments,
                             video_path,
                             output_folder,
                             int(selected_segment_time))
        elif stopped_function_name_flag == "cut_video_by_timecodes":
            start_processing(cut_video_by_timecodes,
                             video_path,
                             segments_times,
                             output_folder)
        elif stopped_function_name_flag == "cut_and_segment_video_by_timecodes":
            start_processing(cut_and_segment_video_by_timecodes,
                             video_path,
                             segments_times,
                             output_folder,
                             int(selected_segment_time))
        start_progressbar()

    else:
        stopping_cutting_video_flag=1
        stop_progressbar()

def start_progressbar():
    progress_bar.start(interval=10) # Запуск индикатора загрузки с интервалом 10 миллисекунд
    progress_bar.grid()  # Показать прогресс-бар


def stop_progressbar():
    progress_bar.stop()
    progress_bar.grid_remove()  # Скрыть прогресс-бар


main_bg_color = "#011627"
button_bg_color = "#9197ae"
text_bg_color = "#2ec4b6"

window = tk.Tk()
window.title("Video Cutter")

window.configure(bg = main_bg_color)
# window.geometry('1200x600')
window_width = 1400
window_height = 620
center_window(window, window_width, window_height)

# Создаем отдельный холст для элементов интерфейса
left_canvas = tk.Canvas(window, width=300, height=600, bg=main_bg_color, highlightthickness=0)
left_canvas.grid(row=0, column=0, rowspan=10, padx=25, pady=5, sticky="nsew")

project_name_select_button_label = tk.Label(left_canvas, text="Название проекта:",font=('Classic Console Neue',15), bg=main_bg_color, fg="white")
project_name_select_button_label.grid(row=0, column=0, padx=0, pady=10, sticky="w")
project_name_select_button = tk.Button(left_canvas, text="Выбрать",font=('Classic Console Neue',13),bg=button_bg_color, command=select_project_name)
project_name_select_button.grid(row=0, column=1, padx=5, pady=10)

project_name_label = tk.Label(left_canvas, text="Название проекта -->", font=('Classic Console Neue',11), bg=main_bg_color, fg="#eca0ff")
project_name_label.grid(row=1, column=0, padx=0, pady=10, sticky="w")

savepath_select_button_label = tk.Label(left_canvas, text="Куда сохранять:", font=('Classic Console Neue',13), bg=main_bg_color, fg="white")
savepath_select_button_label.grid(row=2, column=0, padx=0, pady=10, sticky="w")
savepath_select_button = tk.Button(left_canvas, text="Выбрать", font=('Classic Console Neue',13),bg=button_bg_color, command=select_savepath)
savepath_select_button.grid(row=2, column=1, padx=5, pady=10)

savepath_label = tk.Label(left_canvas, text=f"Путь для сохранения файлов -->{output_folder[:22]}", font=('Classic Console Neue',11), bg=main_bg_color,fg="#eca0ff")
savepath_label.grid(row=3, column=0, padx=0, pady=10, sticky="w")

file_label = tk.Label(left_canvas, text="Выберете .mp4 файл:", font=('Classic Console Neue',13),bg=main_bg_color, fg="white")
file_label.grid(row=4, column=0, padx=0, pady=10, sticky="w")

select_button = tk.Button(left_canvas, text="Выбрать", font=('Classic Console Neue',13),bg=button_bg_color, command=select_file)
select_button.grid(row=4, column=1, padx=5, pady=10)

video_label = tk.Label(left_canvas, text="Выбранный файл:", font=('Classic Console Neue',13),bg=main_bg_color, fg="#eca0ff")
video_label.grid(row=5, column=0, padx=0, pady=10, columnspan=2, sticky="w")

canvas_video = tk.Canvas(left_canvas, bg="white", width=300, height=200)
canvas_video.grid(row=6, column=0, columnspan=2, padx=0, pady=10, sticky="w")
canvas_video.create_text(150, 100, text="Выберете видео", font=('Classic Console Neue',13), fill="#eca0ff")
canvas_video.configure(bg="#273043")

create_timecodes_button = tk.Button(left_canvas, text="Создать таймкоды из ссылки на ролик", font=('Classic Console Neue',13),bg=button_bg_color, command=create_timecodes)
create_timecodes_button.grid(row=7, column=0, columnspan=2, padx=0, pady=10, sticky="w")

view_timecodes_button = tk.Button(left_canvas, text="Посмотреть или изменить таймкоды", font=('Classic Console Neue',13),bg=button_bg_color, command=open_timecodes_table)
view_timecodes_button.grid(row=8, column=0, columnspan=2, padx=0, pady=10, sticky="w")

# Создание общего холста для кнопок и меток
right_canvas = tk.Canvas(window, width=800, height=300, bg = main_bg_color, highlightthickness=0)
right_canvas.grid(row=0, column=3, columnspan=3, rowspan=2, padx=25, pady=5, sticky="w")

# Создание рамки для кнопок
buttons_frame = tk.Frame(right_canvas)
buttons_frame.configure(bg = main_bg_color)
buttons_frame.grid(row=0, column=0, padx=10, pady=10, sticky="w")

# Кнопки
equal_time_button_flag = tk.BooleanVar()
timecodes_button_flag = tk.BooleanVar()
segments_button_flag = tk.BooleanVar()
timecodes_existance_flag = False
equal_time_button = tk.Button(buttons_frame, text="Нарезать равномерно по времени сегмента", font=('Classic Console Neue',10),bg=button_bg_color,
                              command=lambda: start_processing(cut_video_by_segments,
                                                               video_path,
                                                               output_folder,
                                                               int(selected_segment_time)))
equal_time_button.grid(row=0, column=0, padx=10)

timecodes_button = tk.Button(buttons_frame, text="Нарезать просто по таймкодам", font=('Classic Console Neue',10),bg=button_bg_color,
                             command=lambda: start_processing(cut_video_by_timecodes,
                                                              video_path,
                                                              segments_times,
                                                              output_folder))
timecodes_button.grid(row=0, column=1, padx=10)

segments_button = tk.Button(buttons_frame, text="Нарезать по таймкодам + сегментам", font=('Classic Console Neue',10),bg=button_bg_color,
                            command=lambda: start_processing(cut_and_segment_video_by_timecodes,
                                                             video_path,
                                                             segments_times,
                                                             output_folder,
                                                             int(selected_segment_time)))
segments_button.grid(row=0, column=2, padx=10)

# Создание рамки для меток
labels_frame = tk.Frame(right_canvas)
labels_frame.configure(bg = main_bg_color)
labels_frame.grid(row=1, column=0, padx=10, pady=10, sticky="w")

# Метки
segment_time_label = tk.Label(labels_frame, text="Время одного сегмента -->   _______секунд", font=('Classic Console Neue',13), fg="#eca0ff")
segment_time_label.configure(bg = main_bg_color)
segment_time_label.grid(row=0, column=0, sticky="w")

# Кнопка "Указать"
segment_select_button = tk.Button(labels_frame, text="Указать", font=('Classic Console Neue',13),bg=button_bg_color, command=select_segment_time_in_seconds)
segment_select_button.grid(row=0, column=1, padx=10)

# Индикатор загрузки
progress_bar = ttk.Progressbar(labels_frame, mode='indeterminate', maximum=50)
progress_bar.grid(row=0, column=2, padx=10)
progress_bar.grid_remove()  # Скрыть прогресс-бар в начале


# Создание текстового поля для вывода результатов
output_of_result = tk.Text(right_canvas, height=25, width=80)
output_of_result.configure(bg="#273043", fg="#eff6ee", insertbackground="#eff6ee")  # Устанавливаем цвет фона, текста и курсора
output_of_result.grid(row=2, column=0, columnspan=3, padx=25, pady=10, sticky="w")

# Устанавливаем общий шрифт для всего текста в виджете
output_of_result.configure(font=('Classic Console Neue', 13))

# Создаем тег для настройки цвета текста
output_of_result.tag_configure("custom_color", foreground="#eff6ee", font=('Classic Console Neue', 14))

# Вставляем текст с использованием созданного тега
output_of_result.insert(tk.END, "Сюда будут выводиться сохранённые видео\n", "custom_color")


# Создаем рамку для кнопок
bottom_buttons_frame = tk.Frame(right_canvas)
bottom_buttons_frame.configure(bg = main_bg_color)
bottom_buttons_frame.grid(row=3, column=0, columnspan=3, padx=25, pady=10, sticky="w")

# Добавляем stop_button и continue_button в buttons_frame
stop_button = tk.Button(bottom_buttons_frame, text="Остановить нарезку", font=('Classic Console Neue',13), command=lambda: uptade_stop_flag(), bg="#ffa483", fg="black")
stop_button.grid(row=0, column=0, padx=5)

continue_button = tk.Button(bottom_buttons_frame, text="Продолжить нарезку", font=('Classic Console Neue',13), command=lambda: uptade_stop_flag(), bg="#cbffca", fg="black")
continue_button.grid(row=0, column=1, padx=5)


window.mainloop()
