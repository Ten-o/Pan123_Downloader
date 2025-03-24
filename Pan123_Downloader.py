import random
import uuid
import json
import re
import requests
import os
import base64
from tqdm import tqdm
import urllib.parse
import hashlib
from colorama import Fore, init


init(autoreset=True)
class P123:
    def __init__(self, shareKey=input('请输入123云盘的shareKey:')):
        self.save_dir = "download"
        self.headers = self.random_headers()
        self.shareKey = shareKey
        self.USER_FILE = "users.json"
        self.TOKEN_CACHE_FILE = "tokens.json"
        self.tokens = None
        self.login_all_users()


    def load_users(self):
        if os.path.exists(self.USER_FILE):
            with open(self.USER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def load_tokens(self,):
        """加载本地缓存的 tokens"""
        if os.path.exists(self.TOKEN_CACHE_FILE):
            with open(self.TOKEN_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_tokens(self, tokens):
        with open(self.TOKEN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=4, ensure_ascii=False)

    def login(self, user_name, password):
        self.tokens = self.load_tokens()
        if user_name in self.tokens:
            print(f"加载缓存 Token 登录用户: {user_name}")
            return 200  # 成功
        data = {"type": 1, "passport": user_name, "password": password}
        login_res = requests.post(
            "https://www.123pan.com/b/api/user/sign_in",
            headers=self.headers,
            data=data,
        )

        res_sign = login_res.json()
        res_code_login = res_sign["code"]

        if res_code_login != 200:
            print(f"用户 {user_name} 登录失败，错误代码: {res_code_login}")
            print(res_sign.get("message", "未知错误"))
            return res_code_login
        token = res_sign["data"]["token"]
        self.tokens[user_name] = token
        self.save_tokens(self.tokens)
        print(f"用户 {user_name} 登录成功，Token 已缓存。")
        return res_code_login

    def login_all_users(self):
        users = self.load_users()
        if not users:
            print("未找到用户信息，请检查 users.json 文件。")
            return

        for user in users:
            user_name = user["username"]
            password = user["password"]
            self.login(user_name, password)


    def random_headers(self):
        brands = ["Xiaomi", "Samsung", "Huawei", "OnePlus", "Oppo", "Vivo", "Realme"]
        devices = {
            "Xiaomi": ["M2101K9C", "M2012K11AC", "M2010J19SC"],
            "Samsung": ["SM-G991B", "SM-A528B", "SM-M325FV"],
            "Huawei": ["ELE-AL00", "ANA-AL00", "LIO-AL00"],
            "OnePlus": ["KB2001", "IN2020", "BE2028"],
            "Oppo": ["CPH2201", "PDEM30", "PDVM00"],
            "Vivo": ["V2045", "V2025", "V2050"],
            "Realme": ["RMX2081", "RMX3366", "RMX3121"],
        }
        android_versions = ["7.1.2", "8.0.0", "9", "10", "11", "12", "13", "14"]
        brand = random.choice(brands)
        device_model = random.choice(devices[brand])
        android_version = random.choice(android_versions)
        return {
            "user-agent": f"123pan/v2.4.0(Android_{android_version};{brand})",
            "accept-encoding": "gzip",
            "content-type": "application/json",
            "osversion": f"Android_{android_version}",
            "loginuuid": uuid.uuid4().hex,
            "platform": "android",
            "devicetype": device_model,
            "x-channel": "1004",
            "devicename": brand,
            "host": "www.123pan.com",
            "app-version": "61",
            "x-app-version": "2.4.0"
        }

    def get_share(self, ParentFileId=0):
        data = {
            "3278037182": "1742786368-1333383-1007404048",
            "limit": 100,
            "next": -1,
            "orderBy": "file_name",
            "orderDirection": "asc",
            "shareKey": self.shareKey,
            "ParentFileId": ParentFileId,
            "Page": 1,
            "event": "homeListFile",
            "operateType": 1
        }

        share_res = requests.get(
            "https://www.123pan.com/a/api/share/get",
            headers=self.headers,
            data=json.dumps(data),
            timeout=10
        )

        share_json = share_res.json()
        return share_json

    def get_nested_share(self, file_id=0, parent_path=""):
        share_json = self.get_share(file_id)

        if not share_json or not isinstance(share_json, dict):
            return None
        data = share_json.get("data", {}) or {}
        info_list = data.get("InfoList", []) or []
        node = {
            "FileId": file_id,
            "FileName": parent_path if parent_path else "根目录",
            "Type": 1,
            "Children": []
        }
        for item in info_list:
            item_name = item.get("FileName", "未知名称")
            item_path = f"{parent_path}/{item_name}" if parent_path else item_name
            if item.get("Type") == 1:
                sub_folder = self.get_nested_share(item.get("FileId"), item_path)
                if sub_folder:
                    node["Children"].append(sub_folder)

            elif item.get("Type") == 0:
                node["Children"].append({
                    "FileId": item.get("FileId"),
                    "FileName": item_name,
                    "Etag": item.get("Etag"),
                    "S3keyFlag": item.get("S3KeyFlag"),
                    "Type": 0,
                    "Size": item.get("Size"),
                    "Path": item_path
                })
        return node

    def down_info(self,chosen_item ):
        data = {
            "ShareKey": self.shareKey,
            "FileID": chosen_item.get("FileId"),
            "S3keyFlag": chosen_item.get("S3keyFlag"),
            "Size": chosen_item.get("Size"),
            "Etag": chosen_item.get("Etag"),
        }
        if not self.headers.get('Authorization'):
            self.headers[
                'Authorization'] = f'Bearer {random.choice(list(self.tokens.values()))}'

        share_res = requests.post(
            "https://www.123865.com/b/api/share/download/info",
            headers=self.headers,
            data=json.dumps(data),
            timeout=10
        )
        share_json = share_res.json()
        del self.headers['Authorization']
        return share_json.get("data").get('DownloadURL')

    def calc_md5(self, file_path):
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def get_local_file_size(self, filename):
        try:
            return os.path.getsize(os.path.join(self.save_dir, filename))
        except FileNotFoundError:
            return 0

    def download_file(self, url):
        try:
            # 从 URL 中解析 params 参数并解码
            params = url.split("params=")[1].split('&')[0]
            decoded_url = base64.b64decode(params).decode('utf-8')
            parsed_url = urllib.parse.urlparse(decoded_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            filename = query_params.get("filename", [""])[0]

            # 提取文件路径中的 MD5 信息
            path_md5_match = re.search(r'/([a-fA-F0-9]{32})/', parsed_url.path)
            path_md5 = path_md5_match.group(1) if path_md5_match else ""

            # 计算保存路径
            save_path = os.path.join(self.save_dir, filename)

            print(f"\n📂 文件名: {filename}")
            print(f"🔍 MD5: {path_md5}")

            # 获取文件大小
            head_response = requests.head(decoded_url, allow_redirects=True)
            total_size = int(head_response.headers.get("Content-Length", 0))

            if total_size == 0:
                print("⚠️ 无法获取文件大小，可能下载不完整！")

            # 获取本地已下载的文件大小
            downloaded_size = self.get_local_file_size(filename)

            # 如果本地文件大小等于总文件大小，说明已经下载完成
            if downloaded_size >= total_size:
                print(f"✅ 文件已经下载完成: {save_path}")
                return

            # 设置下载请求头
            headers = {"Range": f"bytes={downloaded_size}-{total_size - 1}"} if downloaded_size < total_size else {}

            # 请求并下载文件
            response = requests.get(decoded_url, headers=headers, stream=True, allow_redirects=True)

            # 处理下载
            if response.status_code in (200, 206):
                print(f"📏 文件大小: {total_size / 1024 / 1024:.2f} MB\n")
                mode = "ab" if downloaded_size > 0 else "wb"

                with open(save_path, mode) as f:
                    with tqdm(
                            total=total_size,
                            initial=downloaded_size,
                            unit="B",
                            unit_scale=True,
                            unit_divisor=1024,
                            miniters=1,
                            ascii=True,
                            ncols=100,  # 进度条宽度
                            bar_format="{desc} |{bar}| {percentage:6.2f}% {n_fmt}/{total_fmt}B [{elapsed}<{remaining}, {rate_fmt}]"
                    ) as pbar:
                        pbar.set_description(f"⬇️ {filename}")  # 文件名前缀
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))

                print(f"\n✅ 下载完成: {save_path}")
                local_md5 = self.calc_md5(save_path)
                print(f"本地文件 MD5: {local_md5}")

                if local_md5 == path_md5:
                    print("文件校验通过，下载完整！")
                else:
                    print("文件校验失败，可能下载不完整。")
            else:
                print(f"❌ 下载失败，状态码: {response.status_code}")
                print(f"⚠️ 响应内容预览: {response.text[:200]}")

        except Exception as e:
            print(f"⚠️ 出错了: {e}")

    def choose_download(self, node, parent_node=None):
        print(f"\n{Fore.GREEN}当前目录: {node['FileName']}{Fore.RESET}")
        print(f"  {Fore.RED}-1. 返回上级目录{Fore.RESET}")
        for idx, child in enumerate(node['Children']):
            if child['Type'] == 1:
                # 如果是文件夹，显示文件夹名
                print(f"    {Fore.BLUE}{idx + 1}. {child['FileName']}{Fore.RESET}")
            else:
                # 如果是文件，显示文件名和大小
                size = self.format_size(child['Size'])
                print(f"    {Fore.YELLOW}{idx + 1}. {child['FileName']} ({size}){Fore.RESET}")

        choice = input(f"{Fore.GREEN}请选择要下载的文件或文件夹编号，输入0退出:{Fore.RESET} ")
        try:
            choice = int(choice)
            if choice == -1:
                if parent_node:
                    return self.choose_download(parent_node)
            elif choice == 0:
                return None  # 退出选择
            elif 1 <= choice <= len(node['Children']):
                selected_item = node['Children'][choice - 1]
                if selected_item["Type"] == 1:
                    return self.choose_download(selected_item, node)
                elif selected_item["Type"] == 0:
                    return selected_item
            else:
                print("无效选择，请重新选择。\n")
                return self.choose_download(node, parent_node)
        except ValueError:
            print("输入无效，请输入数字。\n")
            return self.choose_download(node, parent_node)

    def format_size(self, size):
        """格式化文件大小，例如从字节转换为更友好的格式"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 ** 3:
            return f"{size / (1024 ** 2):.2f} MB"
        else:
            return f"{size / (1024 ** 3):.2f} GB"

    def task(self):
        while True:
            final_share_json = self.get_nested_share()
            chosen_item = self.choose_download(final_share_json)
            if chosen_item:
                print(f"用户选择下载: {chosen_item.get('Path')}")
                url = self.down_info(chosen_item)
                self.download_file(url)
#

if __name__ == '__main__':
    a = P123().task()