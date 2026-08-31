"""Shared SMTP send queue for kvant-as apps.

The engine (rate-limited worker threads, retries, priority queue, per-account
rotation) lives here.  Each app keeps only its own subject map and HTML
templates and pushes ready messages in via :func:`get_email_queue`::

    from common_models.mailer import get_email_queue

    get_email_queue().add(to_email, subject, html, email_type="code")

Configuration comes from environment variables:

======================  =======  ==============================================
Variable                Default  Meaning
======================  =======  ==============================================
``SMTP_HOST``           --       SMTP server host (required).
``EMAILS_PER_MINUTE``   6        Per-account send rate.
``EMAILS_DAILY_LIMIT``  10000    Per-account daily cap.
``ACC_<n>_EMAIL`` /              One or more sender accounts, numbered from 1.
``ACC_<n>_PASS``
======================  =======  ==============================================
"""

import os
import time
import uuid
import socket
import smtplib
import logging
from queue import PriorityQueue, Empty
from threading import Thread, Lock
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

__all__ = [
    "get_email_queue",
    "get_email_stats",
    "EmailQueue",
    "safe_email_log",
    "safe_subject_log",
    "PRIORITY",
]

SMTP_HOST = os.getenv("SMTP_HOST")

DEFAULT_EMAILS_PER_MINUTE = int(os.getenv("EMAILS_PER_MINUTE", "6"))
DEFAULT_DAILY_LIMIT = int(os.getenv("EMAILS_DAILY_LIMIT", "10000"))

PRIORITY = {
    "activation_code": 3,
    "code": 3,
    "new_pass": 3,
    "to_admin": 1,
    "to_recipient": 1,
    "default": 0,
}

log = logging.getLogger("email-service")


def safe_email_log(email, show_chars=4):
    if not email or "@" not in email:
        return email

    local, domain = email.split("@", 1)
    if len(local) > show_chars:
        masked_local = local[:show_chars] + "*" * (len(local) - show_chars)
    else:
        masked_local = local + "*" * (show_chars - len(local))
    return f"{masked_local}@{domain}"


def safe_subject_log(subject, max_len=30):
    if not subject:
        return "<пусто>"
    if len(subject) > max_len:
        return subject[:max_len] + "..."
    return subject


class Worker(Thread):
    def __init__(self, email, password, acc_id, queue, emails_per_minute, daily_limit):
        super().__init__(daemon=True)
        self.email = email
        self.password = password
        self.acc_id = acc_id
        self.queue = queue
        self.emails_per_minute = emails_per_minute
        self.daily_limit = daily_limit

        self.sent_today = 0
        self.last_sent = 0
        self.lock = Lock()

        self.stats = {
            "success": 0,
            "failed": 0,
            "retries": 0,
            "connection_errors": 0,
            "auth_errors": 0,
            "timeout_errors": 0,
            "other_errors": 0,
        }
        self.stats_lock = Lock()

        self.start()

    def can_send(self):
        if self.sent_today >= self.daily_limit:
            return False
        if time.time() - self.last_sent < 60 / self.emails_per_minute:
            return False
        return True

    def log_error(self, error_type, port, task_info, error_details, exc_info=False):
        with self.stats_lock:
            self.stats[error_type] = self.stats.get(error_type, 0) + 1

        masked_to = safe_email_log(task_info.get("to", "unknown"))
        masked_subject = safe_subject_log(task_info.get("subject", ""))

        log.error(
            f"[ACC {self.acc_id}] {error_type.upper()} | "
            f"порт:{port} | "
            f"получатель:{masked_to} | "
            f"тема:{masked_subject} | "
            f"попытка:{task_info.get('attempt', 0)} | "
            f"тип:{task_info.get('type', 'unknown')} | "
            f"ошибка:{error_details}",
            exc_info=exc_info,
        )

    def send_email(self, to_email, subject, html, task_info):
        ports_to_try = [465, 587]
        last_error = None

        masked_to = safe_email_log(to_email)
        masked_from = safe_email_log(self.email)

        for port in ports_to_try:
            server = None
            try:
                log.info(
                    f"[ACC {self.acc_id}] Попытка отправки -> {masked_to} через порт {port} "
                    f"(попытка {task_info.get('attempt', 0) + 1})"
                )

                if port == 465:
                    server = smtplib.SMTP_SSL(SMTP_HOST, port, timeout=20)
                else:
                    server = smtplib.SMTP(SMTP_HOST, port, timeout=20)
                    server.starttls()

                server.ehlo()
                server.set_debuglevel(0)

                log.info(f"[ACC {self.acc_id}] Авторизация SMTP ({masked_from})")
                server.login(self.email, self.password)

                msg = MIMEMultipart()
                msg["From"] = self.email
                msg["To"] = to_email
                msg["Subject"] = subject
                msg["Date"] = formatdate(localtime=True)
                msg.attach(MIMEText(html, "html"))

                server.sendmail(self.email, to_email, msg.as_string())
                server.quit()

                with self.lock:
                    self.sent_today += 1
                    self.last_sent = time.time()
                    self.stats["success"] += 1

                log.info(f"[ACC {self.acc_id}] УСПЕХ -> {masked_to} (порт {port})")
                return True

            except smtplib.SMTPAuthenticationError as e:
                self.log_error("auth_errors", port, task_info,
                               f"Ошибка аутентификации: {str(e)[:100]}", exc_info=True)
                last_error = e
                break

            except smtplib.SMTPServerDisconnected as e:
                self.log_error("connection_errors", port, task_info,
                               f"Сервер разорвал соединение: {str(e)[:100]}", exc_info=True)
                last_error = e

            except socket.timeout as e:
                self.log_error("timeout_errors", port, task_info,
                               f"Таймаут соединения: {str(e)[:100]}")
                last_error = e

            except socket.error as e:
                self.log_error("connection_errors", port, task_info,
                               f"Ошибка сокета: {str(e)[:100]}")
                last_error = e

            except smtplib.SMTPException as e:
                error_code = str(e).split()[0] if str(e) else "unknown"
                if error_code.startswith("4"):
                    self.log_error("connection_errors", port, task_info,
                                   f"Временная ошибка SMTP (код {error_code}): {str(e)[:100]}")
                else:
                    self.log_error("other_errors", port, task_info,
                                   f"Постоянная ошибка SMTP (код {error_code}): {str(e)[:100]}")
                last_error = e

            except Exception as e:
                self.log_error("other_errors", port, task_info,
                               f"Неизвестная ошибка: {type(e).__name__}: {str(e)[:100]}", exc_info=True)
                last_error = e

            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass

        with self.stats_lock:
            self.stats["failed"] += 1
        return False

    def run(self):
        consecutive_errors = 0
        last_stats_report = time.time()

        while True:
            try:
                if time.time() - last_stats_report > 3600:
                    with self.stats_lock:
                        log.info(
                            f"[ACC {self.acc_id}] Статистика: успех={self.stats['success']}, "
                            f"ошибок={self.stats['failed']}, соединение={self.stats['connection_errors']}, "
                            f"авторизация={self.stats['auth_errors']}"
                        )
                    last_stats_report = time.time()

                pr, ts, task = self.queue.get(timeout=1)
                consecutive_errors = 0

            except Empty:
                continue

            if not self.can_send():
                time.sleep(5 if consecutive_errors > 0 else 2)
                self.queue.put((pr, ts, task))
                continue

            ok = self.send_email(task["to"], task["subject"], task["html"], task)

            if not ok:
                consecutive_errors += 1
                if task["attempt"] < 3:
                    task["attempt"] += 1
                    wait_time = min(30, 5 * task["attempt"])
                    log.warning(
                        f"[ACC {self.acc_id}] Повтор {task['attempt']}/3 -> "
                        f"{safe_email_log(task['to'])} через {wait_time}с"
                    )
                    with self.stats_lock:
                        self.stats["retries"] += 1
                    time.sleep(wait_time)
                    self.queue.put((pr, time.time(), task))
                else:
                    log.error(
                        f"[ACC {self.acc_id}] ПРОВАЛ -> {safe_email_log(task['to'])} после 3 попыток"
                    )
            else:
                consecutive_errors = 0

            self.queue.task_done()


class EmailQueue:
    def __init__(self, emails_per_minute=None, daily_limit=None):
        self.emails_per_minute = emails_per_minute or DEFAULT_EMAILS_PER_MINUTE
        self.daily_limit = daily_limit or DEFAULT_DAILY_LIMIT
        self.queue = PriorityQueue()
        self.workers = self._load_accounts()
        self.start_time = time.time()

    def _load_accounts(self):
        workers = []
        i = 1
        while True:
            email = os.getenv(f"ACC_{i}_EMAIL")
            password = os.getenv(f"ACC_{i}_PASS")
            if not email or not password:
                break
            workers.append(
                Worker(
                    email=email,
                    password=password,
                    acc_id=i,
                    queue=self.queue,
                    emails_per_minute=self.emails_per_minute,
                    daily_limit=self.daily_limit,
                )
            )
            i += 1

        if not workers:
            raise RuntimeError("No email accounts configured (set ACC_1_EMAIL / ACC_1_PASS)")

        log.info(f"[QUEUE] Загружено {len(workers)} аккаунтов")
        return workers

    def add(self, to_email, subject, html, email_type="default"):
        pr = -PRIORITY.get(email_type, 0)
        task_id = str(uuid.uuid4())[:8]

        task = {
            "id": task_id,
            "to": to_email,
            "subject": subject,
            "html": html,
            "attempt": 0,
            "type": email_type,
            "created_at": time.time(),
        }

        self.queue.put((pr, time.time(), task))

        log.info(
            f"[QUEUE] #{task_id} добавлен | получатель:{safe_email_log(to_email)} | "
            f"тема:{safe_subject_log(subject)} | тип:{email_type} | "
            f"приоритет:{PRIORITY.get(email_type, 0)}"
        )

    def get_stats(self):
        total_stats = {
            "success": 0,
            "failed": 0,
            "retries": 0,
            "connection_errors": 0,
            "auth_errors": 0,
            "timeout_errors": 0,
            "other_errors": 0,
            "queue_size": self.queue.qsize(),
            "uptime": time.time() - self.start_time,
        }
        for worker in self.workers:
            with worker.stats_lock:
                for key in total_stats:
                    if key in worker.stats:
                        total_stats[key] += worker.stats[key]
        return total_stats


_email_queue = None


def get_email_queue(emails_per_minute=None, daily_limit=None):
    """Return the process-wide :class:`EmailQueue`, creating it on first call."""
    global _email_queue
    if _email_queue is None:
        _email_queue = EmailQueue(emails_per_minute, daily_limit)
    return _email_queue


def get_email_stats():
    return get_email_queue().get_stats()
