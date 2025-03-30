#!/usr/bin/env python3

import socket
import os
import stat
from contextlib import nullcontext
from urllib.parse import unquote

from threading import Thread

# Equivalent to CRLF, named NEWLINE for clarity
NEWLINE = "\r\n"


# Let's define some functions to help us deal with files, since reading them
# and returning their data is going to be a very common operation.

def get_file_contents(file_name):
    """Returns the text content of `file_name`"""
    with open(file_name, "r") as f:
        return f.read()


def get_file_binary_contents(file_name):
    """Returns the binary content of `file_name`"""
    with open(file_name, "rb") as f:
        return f.read()


def has_permission_other(file_name):
    """Returns `True` if the `file_name` has read permission on other group

    In Unix based architectures, permissions are divided into three groups:

    1. Owner
    2. Group
    3. Other

    When someone requests a file, we want to verify that we've allowed
    non-owners (and non group) people to read it before sending the data over.
    """
    stmode = os.stat(file_name).st_mode
    return getattr(stat, "S_IROTH") & stmode > 0


# Some files should be read in plain text, whereas others should be read
# as binary. To maintain a mapping from file types to their expected form, we
# have a `set` that maintains membership of file extensions expected in binary.
# We've defined a starting point for this set, which you may add to as
# necessary.
# TODO: Finish this set with all relevant files types that should be read in
# binary
binary_type_files = {"jpg", "jpeg", "png", "bmp", "gif", "mpeg", "mp4", "mp3", "wav", "pdf"}


def should_return_binary(file_extension):
    """
    Returns `True` if the file with `file_extension` should be sent back as
    binary.
    """
    return file_extension in binary_type_files


# For a client to know what sort of file you're returning, it must have what's
# called a MIME type. We will maintain a `dictionary` mapping file extensions
# to their MIME type so that we may easily access the correct type when
# responding to requests.
mime_types = {
    "html": "text/html",
    "css": "text/css",
    "aac": "audio/aac",
    "abw": "application/x-abiword",
    "apng": "image/apng",
    "arc": "application/x-freearc",
    "avif": "image/avif",
    "avi": "video/x-msvideo",
    "azw": "application/vnd.amazon.ebook",
    "bin": "application/octet-stream",
    "bmp": "image/bmp",
    "bz": "application/x-bzip",
    "bz2": "application/x-bzip2",
    "cda": "application/x-cdf",
    "csh": "application/x-csh",
    "csv": "text/csv",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "epub": "application/epub+zip",
    "gz": "application/x-gzip",
    "gif": "image/gif",
    "htm": "text/html",
    "ico": "image/vnd.microsoft.icon",
    "ics": "text/calendar",
    "jar": "application/java-archive",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "js": "application/javascript",
    "json": "application/json",
    "jsonld": "application/ld+json",
    "midi": "audio/x-midi",
    "mid": "audio/midi",
    "mjs": "text/javascript",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "mpeg": "video/mpeg",
    "mpkg": "application/vdn.apple.installer+xml",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "odt": "application/vnd.oasis.opendocument.text",
    "oga": "audio/ogg",
    "ogv": "video/ogg",
    "ogx": "application/ogg",
    "opus": "audio/ogg",
    "otf": "font/otf",
    "png": "image/png",
    "pdf": "application/pdf",
    "php": "application/x-httpd-php",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "rar": "application/rar",
    "rtf": "application/rtf",
    "sh": "application/x-sh",
    "svg": "image/svg+xml",
    "tar": "application/tar",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "ts": "video/mp2t",
    "ttf": "font/ttf",
    "txt": "text/plain",
    "vsd": "application/vnd.visio",
    "wav": "audio/wav",
    "weba": "audio/weba",
    "webm": "video/webm",
    "webp": "video/webp",
    "woff": "font/woff",
    "woff2": "font/woff2",
    "xhtml": "application/xhtml+xml",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xml": "application/xml",
    "xul": "application/vnd.mozilla.xul+xml",
    "zip": "application/zip",
    "3gp": "video/3gpp",
    "3g2": "video/3g2",
    ".7z": "application/x-7z-compressed"
}


def get_file_mime_type(file_extension):
    """
    Returns the MIME type for `file_extension` if present, otherwise
    returns the MIME type for plain text.
    """
    mime_type = mime_types[file_extension]
    return mime_type if mime_type is not None else "text/plain"


def submission_to_table(data):
    return f'''
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Event Submission</title>
            <link rel="stylesheet" href="/styles.css">
        </head>
        <body>
            <nav class="navbar">
                <a href="/" class="logo"><img src="/img/favicon.ico" alt="CSCI4131 icon"></a>
                <div class="nav-links">
                    <a href="/aboutme">About Me</a>
                    <a href="/myschedule">My Schedule</a>
                    <a href="/myform">Form Input</a>
                </div>
            </nav>
            <h1>My New Event</h1>
            <div class="main schedule-main" style="display: block; position: relative;">
                <div class="main-left" style="width: 100%;">
                    <table>
                        <thead>
                            <tr>
                                <th>Event</th>
                                <th>Day</th>
                                <th>Start</th>
                                <th>End</th>
                                <th>Phone</th>
                                <th>Location</th>
                                <th>URL</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{data["event"]}</td>
                                <td>{data["day"]}</td>
                                <td>{data["start"]}</td>
                                <td>{data["end"]}</td>
                                <td>{data["phone"]}</td>
                                <td>{data["location"]}</td>
                                <td><a href="{data['url']}">More Info</a></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <footer>
                <div class="footer-container">
                    <div class="footer-left">
                        <div class="footer-links">
                            <a href="https://www.linkedin.com/in/gustavo-sakamoto-de-toledo-3120a0240/">LinkedIn</a>
                            <a href="mailto:gustavosakamotox@gmail.com">Email</a>
                            <a href="https://www.instagram.com/gustavo.sakamoto.toledo/">Instagram</a>
                        </div>
                    </div>
                </div>
                <p>&copy; Copyright 2025 by Gustavo Sakamoto de Toledo</p>
            </footer>
        </body>
    </html>
    '''


def redirect_handler(query_string):
    params = query_string.split('&')
    search_query = ""

    for param in params:
        if '=' in param:
            key, value = param.split('=', 1)
            if key == 'query_string':
                search_query = unquote(value.replace('+', ' '))
                break
    location = f'https://www.youtube.com/results?search_query={search_query}'
    response = (f'HTTP/1.1 307 TEMPORARY REDIRECT{NEWLINE}'
                f'Location: {location}{NEWLINE}'
                f'Connection: closed{NEWLINE}{NEWLINE}')
    return response.encode('utf-8')


class HTTPServer:
    """
    Our actual HTTP server which will service GET and POST requests.
    """

    def __init__(self, host="localhost", port=4131, directory="."):
        print(f"Server started. Listening at http://{host}:{port}/")
        self.host = host
        self.port = port
        self.working_dir = directory

        self.setup_socket()
        self.accept()

        self.teardown_socket()

    def setup_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(128)

    def teardown_socket(self):
        if self.sock is not None:
            self.sock.shutdown()
            self.sock.close()

    def accept(self):
        while True:
            (client, address) = self.sock.accept()
            th = Thread(target=self.accept_request, args=(client, address))
            th.start()

    def accept_request(self, client_sock, client_addr):
        data = client_sock.recv(4096)
        req = data.decode("utf-8")

        response = self.process_response(req)
        client_sock.send(response)

        # clean up
        client_sock.shutdown(1)
        client_sock.close()

    def process_response(self, request):
        formatted_data = request.strip().split(NEWLINE)
        request_words = formatted_data[0].split()

        if len(request_words) == 0:
            return

        requested_file = request_words[1][1:]
        if request_words[0] == "GET":
            return self.get_request(requested_file, formatted_data)
        if request_words[0] == "POST":
            return self.post_request(requested_file, formatted_data)
        return self.method_not_allowed()

    def head_request(self, requested_file, data) -> bytes:
        if requested_file.endswith('.html'):
            filename = os.path.basename(requested_file)
            requested_file = os.path.join('static', 'html', filename)
        requested_file = os.path.join('.', requested_file)
        file_size = os.path.getsize(requested_file)
        print("\nRequested File: ", requested_file)

        if not os.path.exists(requested_file):
            return self.resource_not_found()
        elif not has_permission_other(requested_file):
            return self.resource_forbidden()
        else:
            header = f'HTTP/1.1 200 OK{NEWLINE}'
            try:
                file_extension = os.path.splitext(requested_file)[1][1:]
                mime_type = get_file_mime_type(file_extension)
            except KeyError:
                mime_type = "text/plain"
            header += f'Content-Length: {file_size}{NEWLINE}'
            header += f'Content-type: {mime_type}{NEWLINE}'
            header += f'Connection: close{NEWLINE}{NEWLINE}'
            return header.encode("utf-8")

    # TODO: Write the response to a GET request
    def get_request(self, requested_file, data) -> bytes:
        """
        Responds to a GET request with the associated bytes.

        If the request is to a file that does not exist, returns
        a `NOT FOUND` error.

        If the request is to a file that does not have the `other`
        read permission, returns a `FORBIDDEN` error.

        Otherwise, we must read the requested file's content, either
        in binary or text depending on `should_return_binary` and
        send it back with a status set and appropriate mime type
        depending on `get_file_mime_type`.
        """
        if requested_file.startswith('redirect'):
            if '?' in requested_file:
                _, query_string = requested_file.split('?', 1)
                return redirect_handler(query_string)
            else:
                return self.resource_not_found()

        if requested_file.endswith('.html'):
            filename = os.path.basename(requested_file)
            requested_file = os.path.join('static', 'html', filename)

        requested_file = os.path.join('.', requested_file)
        print("\nRequested File: ", requested_file)

        if not os.path.exists(requested_file):
            return self.resource_not_found()
        elif not has_permission_other(requested_file):
            return self.resource_forbidden()
        else:
            header = f'HTTP/1.1 200 OK{NEWLINE}'
            file_extension = None
            try:
                file_extension = os.path.splitext(requested_file)[1][1:]
                mime_type = get_file_mime_type(file_extension)
            except KeyError:
                mime_type = "text/plain"
            header += f'Content-type: {mime_type}{NEWLINE}'
            header += f'Connection: close{NEWLINE}{NEWLINE}'
            if should_return_binary(file_extension):
                content = get_file_binary_contents(requested_file)
            else:
                content = get_file_contents(requested_file).encode("utf-8")
            return header.encode("utf-8") + content

    # TODO: Write the response to a POST request
    def post_request(self, requested_file: str, data: list) -> bytes:
        """
        Responds to a POST request with an HTML page containing a table
        where each row corresponds to the field name, and field value from
        the "myform.html" form submission.

        A post request through the form will send over key value pairs
        through "x-www-form-urlencoded" format. You may learn more about
        that here:
          https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST
        You /do not/ need to check the POST request's Content-Type to
        verify the encoding used (although a real server would).

        Care should be taken in forming values with spaces. Since the request
        was urlencoded, it will need to be decoded using
        `urllib.parse.unquote` or `urllib.parse.unquote_plus`.

        Note: When the "myform.html" form is submitted with each field 
        filled, each row should contain a name and value, however, since 
        this function responds to each POST request, it's possible that 
        the contents of the POST request don't conform to what your form is 
        set to submit. In that case, you should ignore additional fields, 
        and also gracefully handle missing fields. 
        """
        content_length = 0
        for line in data:
            if line.lower().startswith('content-length'):
                content_length = int(line.split(':')[1].strip())
                break

        body_lines = []
        body_started = False
        for line in data:
            if line == '':
                body_started = True
                continue
            if body_started:
                body_lines.append(line)
        post_data = "".join(body_lines)[:content_length]

        parsed_data = {}
        for pair in post_data.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                decoded_key = unquote(key)
                decoded_value = unquote(value.replace("+", " "))
                parsed_data[decoded_key] = decoded_value

        html_content = ""
        if requested_file == 'EventLog':
            html_content = submission_to_table(parsed_data)

        response = (
            f"HTTP/1.1 200 OK{NEWLINE}"
            f"Content-Type: text/html{NEWLINE}"
            f"Connection: close{NEWLINE}{NEWLINE}"
            f"{html_content}"
        )
        return response.encode("utf-8")

    def method_not_allowed(self) -> bytes:
        """
        Returns 405 not allowed status and gives allowed methods.
        
        """
        message = f"HTTP/1.1 405 METHOD NOT ALLOWED" \
                  + NEWLINE + NEWLINE.join(["Allow: GET,POST, HEAD", "Connection: close"]) \
                  + NEWLINE + NEWLINE

        return message.encode("utf-8")

    # TODO: Make a function that handles not found error
    def resource_not_found(self) -> bytes:
        """
        Returns 404 not found status and sends back our 404.html page.
        """
        content = ""
        try:
            content = get_file_contents(os.path.join('.', 'static', 'html', '404.html'))
        except FileNotFoundError:
            print("404 Not Found")
        finally:
            message = (f'HTTP/1.1 404 NOT FOUND{NEWLINE}'
                       f'Content-Type: text/html{NEWLINE}'
                       f'Connection: close{NEWLINE}{NEWLINE}'
                       f'{content}').encode("utf-8")
        return message

    # TODO: Make a function that handles forbidden error
    def resource_forbidden(self) -> bytes:
        """
        Returns 403 FORBIDDEN status and sends back our 403.html page.
        """
        content = ""
        try:
            content = get_file_contents(os.path.join('.', 'static', 'html', '403.html'))
        except FileNotFoundError:
            print("404 Not Found")
        finally:
            message = (f'HTTP/1.1 403 FORBIDDEN{NEWLINE}'
                       f'Content-Type: text/html{NEWLINE}'
                       f'Connection: close{NEWLINE}{NEWLINE}'
                       f'{content}').encode("utf-8")
        return message


if __name__ == "__main__":
    HTTPServer()
