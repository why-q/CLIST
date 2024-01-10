import re
import logging
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from langchain_community.document_loaders import SeleniumURLLoader

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clist.db"
db = SQLAlchemy(app)


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=False)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        title = request.form["title"].strip()

        # 如果标题为空，从 URL 爬取标题
        logging.info(f"Input title: {title}")
        if not title:
            try:
                title = get_title_by_url(url)
                logging.info(f"Get title from url: {title}")
                if title is None:
                    title = url
            except Exception as e:
                title = url  # 如果爬取失败，使用 URL 作为标题

        # 保存到数据库
        new_entry = Entry(url=url, title=title)
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for("index"))

    entries = Entry.query.all()
    return render_template("index.html", entries=entries)


@app.route("/delete/<int:entry_id>")
def delete_entry(entry_id):
    entry_to_delete = Entry.query.get_or_404(entry_id)
    db.session.delete(entry_to_delete)
    db.session.commit()
    return redirect(url_for("index"))


def get_title_by_url(url: str) -> str | None:
    logging.info("Getting title by url...")
    loader = SeleniumURLLoader(urls=[url])
    datas = loader.load()
    data = datas[0]
    title = data.metadata["title"]

    type_of_url = get_special_type_of_url(url=url)
    if type_of_url == "wechat":
        idx = data.page_content.find("\n")
        if idx != -1:
            title = data.page_content[:idx].rstrip()
    if type_of_url == "telegraph":
        if title.endswith(" – Telegraph"):
            title = title.replace(" – Telegraph", "")
    if type_of_url == "sspai":
        if title.endswith(" - 少数派"):
            title = title.replace(" - 少数派", "")

    logging.info("Done.")
    return title


def get_special_type_of_url(url):
    if re.search(r"https://github\.com", url):
        return "github"
    elif re.search(r"https://telegra\.ph", url):
        return "telegraph"
    elif re.search(r"https://mp\.weixin\.qq\.com", url):
        return "wechat"
    elif re.search(r"https://arxiv\.org", url):
        return "arxiv"
    elif re.search(r"https://zhuanlan\.zhihu\.com", url):
        return "zhihu"
    elif re.search(r"https://sspai\.com", url):
        return "sspai"
    else:
        return "others"


def setup_logging():
    logging.basicConfig(
        filename="./clist.log",
        filemode="w",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )


if __name__ == "__main__":
    setup_logging()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
