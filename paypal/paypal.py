__author__ = 'Selim Docquir'

import requests, arrow, time, sys
from requests.adapters import HTTPAdapter
from lxml import html
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementNotVisibleException, ElementNotSelectableException
import Tkinter as tk

modes = [('Browserless', 1), ('PhantomJS', 2)]
connect_timeout = 10.0
read_timeout = 10.0


class PaypalBot():
    def __init__(self):
        self.pp_url = 'https://paypal.com'
        self.pp_domain = ".paypal.com"
        self.buy_now_url = 'https://www.paypal.com/cgi-bin/webscr'
        self.product_url = ''
        self.html = None
        self.tree = None
        self.button_id = None
        self.button_index = 0
        self.delay = 1
        self.email = ''
        self.password = ''
        self.mode = 1
        self.checkout_url = None
        self.button_response = None
        self.refresh_count = 0
        self.load_text_files()
        self.get_info()
        self.print_info()
        if self.mode == 2: # PhantomJS setup
            self.driver = webdriver.PhantomJS()
            self.driver.set_window_size(1280, 720)
            self.driver.implicitly_wait(10)
            self.driver.get(self.pp_url)
        self.session = requests.Session()
        self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=20))
        self.session.get(self.pp_url)

    def load_text_files(self):
        with open('paypal/text_files/url.txt', 'r') as file:
            self.product_url = file.read()

        with open('paypal/text_files/refresh_delay.txt', 'r') as f:
            self.delay = float(f.read().lower())

    def get_info(self):
        root = tk.Tk()

        email = tk.StringVar()
        password = tk.StringVar()
        url = tk.StringVar()
        index = tk.IntVar()
        url.set(self.product_url)
        index.set(1)
        mod = tk.IntVar()
        mod.set(1)


        def tk_exit(self):
            self.email = email.get()
            self.password = password.get()
            self.product_url = url.get()
            self.mode = mod.get()
            self.button_index = int(index.get()) - 1  ## minus to show user regular index
            root.destroy()

        tk.Label(root, text="Email: ").grid(column=1, row=1)
        tk.Label(root, text="Password: ").grid(column=1, row=2)
        tk.Label(root, text="URL: ").grid(column=1, row = 3)
        tk.Label(root, text="Button #: ").grid(column=1, row=4)
        tk.Entry(root, textvariable=email).grid(column=2, row=1)
        tk.Entry(root, textvariable=password).grid(column=2, row=2)
        tk.Entry(root, textvariable=url).grid(column=2, row=3)
        tk.OptionMenu(root, index, '1', '2', '3', '4', '5', '6', '7','8','9',).grid(column=2, row=4)
        for txt, val in  modes:
            tk.Radiobutton(root, text=txt, padx=20, variable=mod,
                           command=mod.get(), value=val).grid(row=5, column=val)
        tk.Button(root, text='Submit', command=lambda: tk_exit(self), ).grid(row=6, column=1)
        tk.Button(root, text='Quit', command=sys.exit).grid(row=6, column=2)
        root.mainloop()

    def print_info(self):
        print 'Email:       ', self.email
        print 'URL:         ', self.product_url
        print 'Delay:       ', self.delay
        print 'Button #:    ', (self.button_index + 1)


    def full_purchase(self):
        self.find_buttons()
        print arrow.now().time()
        print 'Found paypal buttons'
        self.click_button()
        print 'Clicked paypal button'
        if self.html.find('Your shopping cart') != -1:
            print 'Cart system detected, starting checkout'
            self.start_checkout()
        if self.mode == 1: # browserless
            print 'Going browserless for remainder of checkout'
            self.login()
            print "Logged in to paypal"
            self.pay()
            print 'Clicked Pay Now'
            self.check_completion()
            print arrow.now().time()
        elif self.mode == 2: # PhantomJS
            print 'Going PhantomJS for remainder of checkout'
            self.open_browser()
            self.login_browser()
            print 'Logged in to paypal'
            self.pay_browser()
            print 'Clicked Pay Now'
            self.check_completion_browser()
            print arrow.now().time()


    def find_buttons(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'}

        while self.button_id is None:
            response = self.session.get(self.product_url, headers=headers, timeout=(connect_timeout, read_timeout))
            self.save_response(response)
            if len(self.tree.xpath('//input[@name="hosted_button_id"]/@value')) > self.button_index:
                self.button_id = self.tree.xpath('//input[@name="hosted_button_id"]/@value')[self.button_index]
                self.save_page('store')
            self.refresh_count += 1
            print "Refresh #", str(self.refresh_count) + '\r',
            time.sleep(self.delay)

    def click_button(self):
        data = {'hosted_button_id': self.button_id,
                'cmd': '_s-xclick'}
        response = self.session.post(self.buy_now_url, data=data)
        self.save_response(response)
        self.save_page('button-clicked')

    def button_step(self):
        self.click_button()
        # while self.button_cookie_len < self.cookie_len:
        #     print 'Going into loop'
        #     self.session = requests.Session()
        #     self.click_button()


    def start_checkout(self):
        url = self.tree.xpath('//form[@method="post"]/@action')
        CONTEXT = self.tree.xpath('//input[@name="CONTEXT"]/@value')
        auth = self.tree.xpath('//form[@method="post"]/input[@name="auth"]/@value')
        data = {'cmd': '_flow',
                'CONTEXT': CONTEXT[0],
                'auth': auth[0],
                'q0': '1',
                'pp_checkout': 'Check out with Paypal',}
        response = self.session.post(url[0], data=data)
        self.save_response(response)
        self.save_page('cart')

    def login_browser(self):
        self.driver.find_element_by_id('login_email').send_keys(self.email)
        self.driver.find_element_by_id('login_password').send_keys(self.password)
        self.driver.find_element_by_name('login.x').click()
        self.save_screenshot('login')

    def login(self):
        url = self.tree.xpath('//form[@id="parentForm"]/@action')
        auth = self.tree.xpath('//form[@id="parentForm"]/input[@name="auth"]/@value')
        SESSION = self.tree.xpath('//input[@id="pageSession"]/@value')
        dispatch = self.tree.xpath('//input[@name="dispatch"]/@value')
        CONTEXT = self.tree.xpath('//input[@name="CONTEXT"]/@value')
        currentSession = self.tree.xpath('//input[@name="currentSession"]/@value')
        currentDispatch = self.tree.xpath('//input[@name="currentDispatch"]/@value')
        data = {'login_email': self.email,
                'login_password': self.password,
                'auth': auth[0],
                'SESSION': SESSION[0],
                'dispatch': dispatch[0],
                'CONTEXT': CONTEXT[0],
                'currentSession':currentSession[0],
                'currentDispatch': currentDispatch[0],
                'login.x': 'Log In',
                'cmd': '_flow',
                'reviewPgReturn': '1',
                'pageState': 'login',
                'email_recovery': 'false',
                'password_recovery': 'false',
                'close_external_flow': 'false',
                'external_close_account_payment_flow': 'payment_flow',
                'pageServerName': 'merchantpaymentweb',
                'flow_name': 'xpt/Checkout/wps/Login'
                }
        response = self.session.post(url[0], data=data)
        self.save_response(response)
        self.save_page('login')

    def pay_browser(self):
        succeeded = False
        self.driver.implicitly_wait(5)
        while succeeded is False:
            try:
                self.driver.find_element_by_name('continue').click()
                succeeded = True
                print 'Clicked Pay now'
            except (NoSuchElementException,
                    ElementNotVisibleException,
                    ElementNotSelectableException):
                try:
                    self.driver.find_element_by_id('cancelBabySlider').click()
                    print 'cancelled credit offer'
                except (NoSuchElementException,
                        ElementNotVisibleException,
                        ElementNotSelectableException):
                    pass
        self.save_screenshot('pay')

    def pay(self):
        url = self.tree.xpath('//form[@method="post"]/@action')
        auth = self.tree.xpath('//form[@method="post"]/input[@name="auth"]/@value')
        SESSION = self.tree.xpath('//input[@name="SESSION"]/@value')
        dispatch = self.tree.xpath('//input[@name="dispatch"]/@value')
        CONTEXT = self.tree.xpath('//input[@name="CONTEXT"]/@value')
        currentSession = self.tree.xpath('//input[@name="currentSession"]/@value')
        currentDispatch = self.tree.xpath('//input[@name="currentDispatch"]/@value')
        data = {
                'auth': auth[0],
                'SESSION': SESSION[0],
                'dispatch': dispatch[0],
                'CONTEXT': CONTEXT[0],
                'currentSession':currentSession[0],
                'currentDispatch': currentDispatch[0],
                'continue': 'Pay Now',
                'cmd': '_flow',
                'reviewPgReturn': '1',
                'pageState': 'review',
                'close_external_flow': 'false',
                'external_close_account_payment_flow': 'payment_flow',
                'pageServerName':'merchantpaymentweb',
                }
        response = self.session.post(url[0], data=data)
        self.save_response(response)
        self.save_page('pay')

    def check_completion_browser(self):
        try:
            self.driver.implicitly_wait(10)
            self.driver.find_element_by_id('printReceiptButton')
            print 'Receipt button found, order successful'
        except NoSuchElementException:
            print 'No receipt button found, order unsuccessful'


    def check_completion(self):
        if self.html.find('you just completed your payment') != -1:
            print 'Found transaction ID'
            print
            print 'BOT RUN SUCCESSFUL'

    def open_browser(self):
        se_cookies = []
        for cookie in self.session.cookies:
            if cookie.domain != self.pp_domain:
                continue
            dict = {'domain': cookie.domain,
                    'path': cookie.path,
                    'value': cookie.value,
                    'name': cookie.name}
            se_cookies.append(dict)
        for cookie in se_cookies:
            self.driver.add_cookie(cookie)
        self.driver.get(self.checkout_url)

    def save_response(self, response):
        self.tree = html.fromstring(response.text)
        self.html = response.text
        self.checkout_url = response.url

    def save_screenshot(self, name='default'):
        self.driver.save_screenshot('paypal/orders/{0}-{1}-{2}.png'.format(self.button_index,self.email[:5], name))

    def save_page(self, name='default' ):
        with open('paypal/orders/{0}-{1}-{2}.html'.format(self.button_index,self.email[:5], name), 'w') as file:
            file.write(self.html.encode('UTF-8'))
