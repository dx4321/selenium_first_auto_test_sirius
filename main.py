import re
import time
from enum import Enum
from typing import List

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

import yaml
from pydantic import BaseModel


class Config(BaseModel):
    link: str
    user: str
    password: str


def get_config(yaml_file_name: str):
    with open(yaml_file_name) as f:
        return Config(**yaml.safe_load(f))


class MENU(Enum):
    MENU_ClASS = "menu"

    zones_TEXT = "Состояние объекта"
    live_view_TEXT = "Виртуальная панель"
    log_TEXT = "Журнал событий"
    config_TEXT = "Конфигурация"
    settings_TEXT = "Настройки"

    # Дата (элемент из "Последние события")
    data_ID = "evDate"


class ConfigMenu(Enum):
    controller_CLASS = "controller"         # Контроллеры
    device_CLASS = "device"                 # Приборы
    zone_CLASS = "zone"                     # Зоны
    zone_group_CLASS = "zone_group"         # Группы зон
    program_CLASS = "program"               # Программы
    script_CLASS = "script"                 # Сценарии
    access_group_CLASS = "access_group"     # Группы доступа
    user_CLASS = "user"                     # Пользователи


class ADD_DEVICE(Enum):
    # Добавить Прибор
    add_config_item_CLASS_NAME = "add_config_item"

    # Тип элемента на вкладке (Конфигурация) -> добавить прибор -> тип элемента
    type_select_ID = "type_select"


class ADD_ZONE(Enum):
    # Добавить зону
    add_config_item_CLASS_NAME = "add_config_item"


class ADD_SCRIPT(Enum):
    # Добавить сценарий
    add_config_item_CLASS_NAME = "add_config_item"
    add_step_CLASS_NAME = "add_step"

    # Поля в разделе "добавить шаг"
    Permissive_zones_CELL_TEXT = "Разрешающие зоны"
    Forbidden_zones_CELL_TEXT = "Запрещающие зоны"
    Permissive_States_CELL_TEXT = "Разрешающие состояния"
    Forbidden_states_CELL_TEXT = "Запрещающие состояния"


class Sirius:
    def __init__(self, link_to_login: str, login: str, password: str, delay: int = 3):
        """:param link - IP адрес устройства: http://***.***.**.***"""

        self.delay: int = delay
        self.driver: WebDriver = self.get_driver()
        self.link: str = link_to_login
        self.login: str = login
        self.password: str = password
        self.log_in()

    def exit(self):
        """ Делаем logout и заканчиваем работу драйвера """

        print(f"Нажмите любую кнопку что-бы выйти")

        try:
            input()
        except KeyboardInterrupt:
            pass

        self.driver.find_element(By.XPATH, '//*[@id="user"]/span[2]').click()
        time.sleep(2)
        self.driver.quit()

    def go_to_menu_category(self, go_to_category_id: str):
        """ Взять меню id и внутри него перейти по id нужной нам категории """
        self.wait_load(By.ID, MENU.data_ID.value, 25)  # ждем пока загрузится data
        menu_items = self.driver.find_elements(By.CLASS_NAME, MENU.MENU_ClASS.value)

        for item in menu_items:
            if item.text == go_to_category_id:
                time.sleep(1)
                item.click()
                print(f"Перешли в ({go_to_category_id})")

    @staticmethod
    def get_driver():
        """ Веб драйвер менеджер сам установит необходимый драйвер """

        driver = webdriver.Chrome(service=Service('./chromedriver.exe'))
        driver.maximize_window()
        return driver

    def wait_load(self, by: By, element: str, delay: int = 3):
        """ Дождаться загрузки страницы по id элемента """

        try:
            WebDriverWait(self.driver, delay).until(ec.presence_of_element_located((by, element)))
            return True

        except TimeoutException:
            current_page = self.driver.current_url
            print(f"Загрузка {current_page} заняла слишком много времени!")
            return False

    def wait_for_the_button_and_press(self, by: By, element: str, delay: int = 3):
        """ Дождаться появления element и вернуть его """

        self.wait_load(by, element, delay)
        item = self.driver.find_element(by, element)
        return item

    def find_field_enter_value(self, fild="name", insert_value: str = None):
        """
        Найти поле по id и ввести в него значения
        :param fild: str искомое поле
        :type insert_value: str
        """

        login_form = self.driver.find_element(by=By.ID, value=fild)
        login_form.clear()
        login_form.send_keys(insert_value)

    def log_in(self):
        """ Залогиниться на сайте """

        self.driver.get(self.link)

        assert "Сириус" in self.driver.title

        self.wait_load(By.ID, "name", self.delay)
        self.find_field_enter_value("name", self.login)
        self.find_field_enter_value("password", self.password)
        self.driver.find_element(By.ID, "submit").click()

        while True:
            time.sleep(0.5)

            if self.wait_load(By.CLASS_NAME, MENU.MENU_ClASS.value, 10):
                break

            else:
                print(f"Не получилось войти в учетную запись, пробуем еще раз")
                try:
                    self.driver.find_element(By.ID, "submit").click()

                except NoSuchElementException:
                    pass

    def go_to_config_menu_and_wait_id(self, cat_menu: str, wait_id: By, wait_element: str, delay: int = None):
        """ Перейти подменю в разделе конфигурация """

        self.wait_load(wait_id, wait_element, delay)

        elements_menu: List[WebElement] = self.driver.find_elements(By.XPATH, '//*[@id="configMenu"]/ul/li')

        for element in elements_menu:
            attr = element.get_attribute("class")

            if attr == cat_menu:
                element.click()
                print(f"Перешли в подраздел - {cat_menu}")

            elif attr == (cat_menu + " active"):
                print(f"Уже находимся в разделе - {cat_menu}")
                break

    def add_device(self, device: List[str]):
        """ Добавить прибор """

        # Перейти в категорию конфигурации
        self.go_to_menu_category(MENU.config_TEXT.value)
        time.sleep(1)

        # Перейти в подраздел Приборы
        self.go_to_config_menu_and_wait_id(
            ConfigMenu.device_CLASS.value,                  # Категория меню
            By.CLASS_NAME,                                  # Ожидаем по имени класса
            ADD_DEVICE.add_config_item_CLASS_NAME.value,    # Искомое значение для ожидания
            17                                              # таймаут
        )

        # Дождаться загрузки страницы, и кнопки элемента "добавить прибор" на ней -> нажать добавить
        self.wait_for_the_button_and_press(By.CLASS_NAME, ADD_DEVICE.add_config_item_CLASS_NAME.value, 4).click()
        time.sleep(0.7)

        # Выбрать поле "Тип" и нажать на него
        self.wait_for_the_button_and_press(By.XPATH, f'//*[@id="{ADD_DEVICE.type_select_ID.value}"]', 4).click()

        # Сделать список опционных элементов
        option_list: List[WebElement] = self.driver.find_elements(
            By.XPATH, f'//*[@id="{ADD_DEVICE.type_select_ID.value}"]/option'
        )

        for option in option_list:
            if option.text in device:
                time.sleep(0.5)
                option.click()
                print(f"Выбрали {device}")

        time.sleep(3)

        # Жмем кнопку сохранить
        self.driver.find_element(By.XPATH, '//*[@id="actions"]/input').click()
        print("Нажали сохранить")

    def add_zone(self, _zone_name: str, device: str):
        """ Добавляем зону """

        def select_the_desired_device(dev: str, position: int):
            """
            Выбрать устройство

            :param dev: устройство
            :param position: -1 это предыдущее устройство, 0 - текущее устройство
            :return:
            """

            time.sleep(1)
            self.driver.find_element(By.XPATH, '//*[@id="zones-elems-modal"]/div/div/select').click()
            time.sleep(2)

            # Получить список устройств
            list_devices: List[WebElement] = self.driver.find_elements(
                By.XPATH,
                '//*[@id="zones-elems-modal"]/div/div/select/option'
            )

            i = len(list_devices) - 1

            while i > -1:

                device_element: str = list_devices[i].text

                if dev in device_element:
                    time.sleep(1)

                    if position == 0:
                        list_devices[i].click()
                        print(f"Выбрали нужное устройство {dev}")

                    elif position == -1:
                        list_devices[i - 1].click()
                        print(f"Выбрали нужное устройство {list_devices[i - 1].text}")

                    break

                i -= 1

            # Затем нужно выбрать все выходы
            device_outputs: List[WebElement] = self.driver.find_elements(
                By.XPATH,
                '//*[@id="zones-elems-modal"]/div/div[2]/label'
            )
            for output in device_outputs:
                output.click()

            time.sleep(1)

            # жмем выйти на Х
            self.driver.find_element(By.XPATH, '//*[@id="zones-elems-modal"]/button').click()

        self.go_to_config_menu_and_wait_id(
            ConfigMenu.zone_CLASS.value,
            By.CLASS_NAME,
            ADD_ZONE.add_config_item_CLASS_NAME.value,
            1
        )
        # Нажимаем добавить Зону
        self.wait_for_the_button_and_press(By.CLASS_NAME, ADD_ZONE.add_config_item_CLASS_NAME.value, 2).click()

        # Пишем название зоны
        self.find_field_enter_value("name_input", _zone_name)

        # Находим кнопки добавить вход, добавить выход
        buttons_input_and_output: List[WebElement] = self.driver.find_elements(By.XPATH,
                                                                               '//*[@id="zoneElements"]/button')
        # Жмем добавить вход
        buttons_input_and_output[0].click()
        time.sleep(1.5)

        # Выбрать прибор который мы добавляли {device -> c2000_kdl}
        select_the_desired_device(device, 0)
        time.sleep(1)

        # Нажать сохранить
        self.driver.find_element(By.XPATH, '//*[@id="actions"]/input').click()
        time.sleep(1)
        print("Сохранили зону")

    def add_script(self, zone_add: str):
        """ Добавить сценарий """

        def add_items_to_popup_menu(offset: int):
            """ Добавить элементы во всплывающем меню
                :arg offset - смещение [0 это текущая зона, -1 это предыдущая зона] - из появившегося списка
            """

            _row_button: WebElement = row.find_element(By.CLASS_NAME, 'edit-zone-btn')
            _row_button.click()
            time.sleep(1)

            menu_add_zone: List[WebElement] = self.driver.find_elements(By.XPATH, "/html/body/div/div/ul/li/label")

            i = len(menu_add_zone) - 1

            while i > -1:

                # отрезаем (*+) цифры в скобках и пробел после них
                # использую регулярное выражение
                text: str = re.sub(r"(\(\d+\) )(.+)", r"\2", menu_add_zone[i].text)
                if text == zone_add:
                    if offset == -1:

                        # выбрать предыдущее значение
                        menu_add_zone[i - 1].click()
                        break
                    elif offset == 0:
                        menu_add_zone[i].click()
                        break
                i -= 1

            time.sleep(1)

            # жмем кнопку "X" (закрыть)
            self.driver.find_element(By.XPATH, "/html/body/div/div/button").click()

        def add_items_to_menu_by_button(variant: List[str]):
            """
            Нажать на кнопку "Добавить/Изменить"
            Добавить состояния
            variant - указать список проклеиваемых элементов
            """
            row_button: WebElement = row.find_element(By.CLASS_NAME, 'dv_add_button')
            row_button.click()
            time.sleep(0.5)

            # Получить список всех вариантов
            list_all_variants: List[WebElement] = self.driver.find_elements(
                By.XPATH, '//*[@id="states_list"]/label'
            )
            for variant_in_list in list_all_variants:

                #   Из списка проставить галочки "КЗ ДПЛС"
                if variant_in_list.text in variant:
                    variant_in_list.click()

            # Нажать кнопку "принять"
            list_buttons_accept_decline: List[WebElement] = self.driver.find_elements(
                By.XPATH, '//*[@id="modal_window"]/div/div/div/button'
            )
            list_buttons_accept_decline[0].click()

        # Перейти в меню "Сценарии"
        self.go_to_config_menu_and_wait_id(
            ConfigMenu.script_CLASS.value,
            By.CLASS_NAME,
            ADD_SCRIPT.add_config_item_CLASS_NAME.value,
            12
        )
        time.sleep(1)

        # Нажать на кнопку "Добавить сценарий"
        self.wait_for_the_button_and_press(
            By.CLASS_NAME, ADD_SCRIPT.add_config_item_CLASS_NAME.value,
            1
        ).click()
        time.sleep(1)

        # Нажать кнопку добавить шаг
        self.wait_for_the_button_and_press(
            By.CLASS_NAME, ADD_SCRIPT.add_step_CLASS_NAME.value,
            2
        ).click()

        # Пройти по меню "шага" и выбрать кнопки в соответствующих разделах
        step_menu: List[WebElement] = self.driver.find_elements(By.XPATH, '//*[@id="script_step"]/div')

        for i, row in enumerate(step_menu):

            # Нажать кнопку "разрешающие зоны"
            if row.text == ADD_SCRIPT.Permissive_zones_CELL_TEXT.value:

                # Нажать кнопку "разрешающие зоны"
                # В новом окне выбрать зону которую создали на предыдущем шаге - > затем нажать крест
                add_items_to_popup_menu(0)

            elif row.text == ADD_SCRIPT.Forbidden_zones_CELL_TEXT.value:

                # Нажать кнопку "запрещающие зоны"
                #   Выбрать предыдущую зону из списка - > затем нажать крест
                add_items_to_popup_menu(-1)

            elif ADD_SCRIPT.Permissive_States_CELL_TEXT.value in row.text:

                # В строке "разрешающие состояния" нажать на кнопку "добавить изменить"
                add_items_to_menu_by_button(["КЗ ДПЛС"])

            elif ADD_SCRIPT.Forbidden_states_CELL_TEXT.value in row.text:

                # В строке "Запрещающие состояния" нажать кнопку "Добавить изменить"
                #   Во всплывающем окне выбрать "Норма ДПЛС" -> принять
                add_items_to_menu_by_button(["Норма ДПЛС"])

        time.sleep(0.5)

        # Сохранить
        self.driver.find_element(By.XPATH, '//*[@id="actions"]/input').click()


if __name__ == "__main__":
    config: Config = get_config("config.yaml")
    sirius = Sirius(link_to_login=config.link, login=config.user, password=config.password, delay=3)

    c2000_kdl = "С2000-КДЛ"
    zone_name = "test_zone1"

    # Добавить прибор
    sirius.add_device([c2000_kdl])

    # Добавить зону
    sirius.add_zone(zone_name, c2000_kdl)

    # Перейти в сценарий
    # Есть баг - в реализации выбора в пуктах разрешающие зоны и запрещающие зоны - (договорились что попозже исправим)
    sirius.add_script(zone_name)

    # Ждать нажатия клавиши что-бы завершить работу программы
    sirius.exit()
