# -*- coding: utf-8 -*-
"""Generate the Northgo preview site in Traditional Chinese and English."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

OFFICES = [
    {
        "id": "tpe", "region": "taiwan", "hq": True, "lat": 25.05816, "lng": 121.54523,
        "zh": "台北總部", "en": "Taipei HQ", "short_zh": "台北", "short_en": "Taipei",
        "address_zh": "台北市民生東路三段 10 號 7 樓，104511",
        "address_en": "7F., No. 10, Sec. 3, Minsheng E. Rd., Taipei City 104511, Taiwan",
        "phone": "+886-2-2531-8677", "fax": "+886-2-2531-8577", "email": "info.tpe@northgo.com",
    },
    {
        "id": "txg", "region": "taiwan", "hq": False, "lat": 24.27138, "lng": 120.53068,
        "zh": "台中", "en": "Taichung", "short_zh": "台中", "short_en": "Taichung",
        "address_zh": "台中市中橫十一路 4 號，435058",
        "address_en": "No. 4, Zhongheng 11th Rd., Taichung City 435058, Taiwan",
        "phone": "+886-4-2326-2580", "fax": "+886-4-2326-0308", "email": "info.txg@northgo.com",
    },
    {
        "id": "khh", "region": "taiwan", "hq": False, "lat": 22.61976, "lng": 120.29169,
        "zh": "高雄", "en": "Kaohsiung", "short_zh": "高雄", "short_en": "Kaohsiung",
        "address_zh": "高雄市海邊路 31 號 19 樓之 2，802609",
        "address_en": "19F-2, No. 31 Hai-Pien Rd., Kaohsiung City 802609, Taiwan",
        "phone": "+886-7-335-0730", "fax": "+886-7-336-4536", "email": "info.khh@northgo.com",
    },
    {
        "id": "tyo", "region": "japan", "hq": False, "lat": 35.67242, "lng": 139.77414,
        "zh": "東京", "en": "Tokyo", "short_zh": "東京", "short_en": "Tokyo",
        "address_zh": "東京都中央區新富 1-5-1 Gran+Ginza-East 6 樓，104-0041",
        "address_en": "6F, Gran+Ginza-East, 1-5-1 Shintomi, Chuo-ku, Tokyo 104-0041, Japan",
        "phone": "+81-3-6260-3944", "fax": "+81-3-6260-3945", "email": "info.tyo@northgo.com",
    },
    {
        "id": "osa", "region": "japan", "hq": False, "lat": 34.69731, "lng": 135.49874,
        "zh": "大阪", "en": "Osaka", "short_zh": "大阪", "short_en": "Osaka",
        "address_zh": "大阪市北區曾根崎新地 2-6-23 MF Sakura-Bashi Build 3 樓，530-0002",
        "address_en": "3F, MF Sakura-Bashi Build, 2-6-23 Sonezaki Shinchi, Kita-ku, Osaka 530-0002, Japan",
        "phone": "+81-6-6676-8395", "fax": "+81-6-6676-8397", "email": "info.osa@northgo.com",
    },
    {
        "id": "sgn", "region": "sea", "hq": False, "lat": 10.7927, "lng": 106.7168,
        "zh": "胡志明市", "en": "Ho Chi Minh City", "short_zh": "胡志明市", "short_en": "Ho Chi Minh City",
        "address_zh": "胡志明市平盛郡第 22 坊阮友敬路 92D 號 5 樓",
        "address_en": "5F, 92D Nguyen Huu Canh, Ward 22, Binh Thanh, Ho Chi Minh City, Vietnam",
        "phone": "+84-28-9995-7368", "fax": "", "email": "info.hcmc@northgo.com",
    },
    {
        "id": "lax", "region": "na", "hq": False, "lat": 34.06221, "lng": -118.13431,
        "zh": "洛杉磯", "en": "Los Angeles", "short_zh": "洛杉磯", "short_en": "Los Angeles",
        "address_zh": "119 S. Atlantic Blvd, Ste 301, Monterey Park, CA 91754, USA",
        "address_en": "119 S. Atlantic Blvd, Ste 301, Monterey Park, CA 91754, USA",
        "phone": "+1-714-853-1088", "fax": "", "email": "info.lax@northgo.com",
    },
]

UI = {
    "zh": {
        "lang": "zh-Hant", "skip": "跳至內容", "menu": "選單", "services": "服務",
        "offices": "據點", "scenarios": "服務情境", "about": "關於", "enquire": "詢價",
        "other": "EN", "home": "首頁",
        "freight": "貨運物流", "project": "專案物流", "warehouse": "倉儲物流", "shipping": "船務代理",
        "legal": "法律說明", "privacy": "隱私", "terms": "條款", "cookies": "Cookie", "disclaimer": "聲明",
        "foot": "預覽站，依 2026-11-25 公開官網改寫。正式網站與具約束力的條款仍以 www.northgo.com 為準。本站沒有線上追蹤、運價或庫存系統。",
    },
    "en": {
        "lang": "en", "skip": "Skip to content", "menu": "Menu", "services": "Services",
        "offices": "Offices", "scenarios": "Scenarios", "about": "About", "enquire": "Enquire",
        "other": "繁中", "home": "Home",
        "freight": "Freight", "project": "Project cargo", "warehouse": "Warehousing", "shipping": "Shipping agency",
        "legal": "Legal notes", "privacy": "Privacy", "terms": "Terms", "cookies": "Cookies", "disclaimer": "Disclaimer",
        "foot": "Preview built from the public site as of 2026-11-25. The live site and its binding terms remain at www.northgo.com. This preview has no tracking, rate, or inventory system.",
    },
}

PAGES = {}


def office_name(office, lang):
    return office["zh"] if lang == "zh" else office["en"]


def home(lang):
    t = UI[lang]
    if lang == "zh":
        hero = """
        <p class="kicker">Northgo · Taipei since 1988</p>
        <h1>讓物流變得輕鬆。</h1>
        <p class="lede">四條服務，七個辦公室。海運、空運、陸運與報關由貨運承接；超尺寸走專案；庫存走倉儲；船舶在港走船代。詢價會寄到你選的辦公室，這個網站不查貨況、也不報即時運價。</p>
        <div class="actions"><a class="btn btn-primary" href="freight.html">先看貨運怎麼分</a><a class="btn btn-secondary" href="contact.html">填詢價</a></div>
        """
        services = """
        <section class="section"><h2>四條服務，各做各的</h2>
        <p class="intro">每條服務只寫自己的範圍。不確定該走哪一條，詢價時選「還不確定」。</p>
        <div class="cards services" style="margin-top:16px">
          <article class="card"><p class="kicker">01</p><h3>貨運物流</h3><p>整櫃、併櫃、空運、港口到門的陸運，以及報關文件。一般進出口從這裡開始。</p><a class="more" href="freight.html">看四種方式</a></article>
          <article class="card"><p class="kicker">02</p><h3>專案物流</h3><p>超寬、超重、不好拆、需要吊運或路權的貨物。一般整櫃不要放在這條。</p><a class="more" href="project.html">看要先準備的尺寸</a></article>
          <article class="card"><p class="kicker">03</p><h3>倉儲物流</h3><p>公開資料中的倉儲在台中港：進出倉、揀貨包裝、驗貨。網站上看不到庫存數字。</p><a class="more" href="warehouse.html">看作業範圍</a></article>
          <article class="card"><p class="kicker">04</p><h3>船務代理</h3><p>船舶靠港時的窗口：靠泊協調與港口文件。貨主的貨要另外走貨運或專案。</p><a class="more" href="shipping.html">看跟貨運的差別</a></article>
        </div></section>
        """
        steps = """
        <section class="section"><h2>詢價只要三件事</h2>
        <div class="steps" style="margin-top:16px">
          <div class="card step"><span class="num">1</span><div><h3>選服務</h3><p>不確定就選「還不確定」，信裡寫品名即可。</p></div></div>
          <div class="card step"><span class="num">2</span><div><h3>寫起訖與貨量</h3><p>城市或港口、件數、重量與尺寸。沒有這些資料，辦公室無法報價。</p></div></div>
          <div class="card step"><span class="num">3</span><div><h3>選辦公室</h3><p>信會用你的郵件軟體寄到該據點，例如台北總部是 info.tpe@northgo.com。</p></div></div>
        </div>
        <p style="margin-top:16px"><a class="btn btn-navy" href="contact.html">開始詢價</a></p>
        </section>
        """
        about = """
        <section class="section panel"><h2>公司從哪裡來</h2>
        <p>1988 年在台北創立，當時名稱是 Max Seair Logistics。2024 年 11 月 11 日更名為 Northgo。名字換了，總部仍在台北市民生東路。</p>
        <p style="margin-top:10px"><a class="more" href="about.html">沿革與我們不宣稱的事</a></p></section>
        """
    else:
        hero = """
        <p class="kicker">Northgo · Taipei since 1988</p>
        <h1>Making logistics effortless.</h1>
        <p class="lede">Four services, seven offices. Ocean, air, trucking, and customs sit under freight. Out-of-gauge cargo is project work. Storage is warehousing. A ship in port is agency work. An enquiry goes to the office you pick. This site does not track shipments or show live rates.</p>
        <div class="actions"><a class="btn btn-primary" href="freight.html">See how freight is split</a><a class="btn btn-secondary" href="contact.html">Enquire</a></div>
        """
        services = """
        <section class="section"><h2>Four services, each with a job</h2>
        <p class="intro">Each service states its own scope. If you are unsure which one fits, choose “Not sure yet” on the enquiry.</p>
        <div class="cards services" style="margin-top:16px">
          <article class="card"><p class="kicker">01</p><h3>Freight</h3><p>FCL, LCL, air, port-to-door trucking, and customs paperwork. Ordinary import and export starts here.</p><a class="more" href="freight.html">Four modes</a></article>
          <article class="card"><p class="kicker">02</p><h3>Project cargo</h3><p>Cargo that is too wide, too heavy, hard to split, or needs a lift plan. Do not put a standard container here.</p><a class="more" href="project.html">What to measure first</a></article>
          <article class="card"><p class="kicker">03</p><h3>Warehousing</h3><p>The published warehouse is at Taichung Port: in, out, pick-and-pack, inspection. Stock figures are not on this site.</p><a class="more" href="warehouse.html">Scope of work</a></article>
          <article class="card"><p class="kicker">04</p><h3>Shipping agency</h3><p>The ship’s side of a port call: berth coordination and port papers. The cargo itself is freight or project work.</p><a class="more" href="shipping.html">How this differs from freight</a></article>
        </div></section>
        """
        steps = """
        <section class="section"><h2>Three things an enquiry needs</h2>
        <div class="steps" style="margin-top:16px">
          <div class="card step"><span class="num">1</span><div><h3>Pick a service</h3><p>If you are unsure, say so and name the commodity.</p></div></div>
          <div class="card step"><span class="num">2</span><div><h3>Origin, destination, quantity</h3><p>City or port, pieces, weight, and size. Without that, an office cannot price the job.</p></div></div>
          <div class="card step"><span class="num">3</span><div><h3>Pick an office</h3><p>Your mail app sends the note to that office. Taipei HQ is info.tpe@northgo.com.</p></div></div>
        </div>
        <p style="margin-top:16px"><a class="btn btn-navy" href="contact.html">Start an enquiry</a></p>
        </section>
        """
        about = """
        <section class="section panel"><h2>Where the company comes from</h2>
        <p>Founded in Taipei in 1988 as Max Seair Logistics. Renamed Northgo on 11 November 2024. The headquarters is still on Minsheng East Road.</p>
        <p style="margin-top:10px"><a class="more" href="about.html">History, and what we do not claim</a></p></section>
        """
    route = ['<ol class="route">']
    for office in OFFICES:
        label = office_name(office, lang)
        role = ("總部" if lang == "zh" else "Headquarters") if office["hq"] else ("辦公室" if lang == "zh" else "Office")
        route.append(f'<li><a href="offices.html#{office["id"]}">{label}<span>{role}</span></a></li>')
    route.append("</ol>")
    return f'<section class="hero"><div class="wrap hero-grid"><div>{hero}</div><div>{"".join(route)}</div></div></section><div class="wrap">{services}{steps}{about}</div>'


def freight(lang):
    if lang == "zh":
        return """
        <div class="wrap">
          <p class="kicker">服務 01</p>
          <h1>貨運物流</h1>
          <p class="intro">一般進出口：海運整櫃與併櫃、空運、港口或機場到倉的陸運，以及報關文件。超尺寸走專案物流，庫存走倉儲，船舶靠港走船代。</p>
          <div class="split section">
            <div class="do"><h3>這頁做的事</h3><p>依品名、貨量與起訖，請對的辦公室安排運輸與文件。運價、船期與艙位逐票確認。</p></div>
            <div class="dont"><h3>這頁不做的事</h3><p>沒有線上貨況、沒有即時運價、沒有艙位保證。運價與船期以辦公室回覆為準。</p></div>
          </div>
          <div class="section table-wrap"><table>
            <thead><tr><th>方式</th><th>適合</th><th>先準備</th><th>網站不提供</th></tr></thead>
            <tbody>
              <tr id="ocean"><td>海運</td><td>整櫃 FCL、併櫃 LCL，時效比較寬的貨物。</td><td>品名、櫃型或材積、起訖港、貿易條件。</td><td>即時船期與運價。</td></tr>
              <tr id="air"><td>空運</td><td>時效優先、體積重量敏感的貨物。</td><td>件數、毛重、長寬高。</td><td>艙位保證。</td></tr>
              <tr id="land"><td>陸運</td><td>港口、機場、倉庫與工廠之間的拖車或卡車。</td><td>地址、時間窗、車高或車重限制。</td><td>車輛即時位置。</td></tr>
              <tr id="customs"><td>報關</td><td>進出口需要正式申報時，協助整理 HS Code 與文件。</td><td>商業發票、裝箱單、既有稅則建議。</td><td>稅費試算。稅費以海關核定為準。</td></tr>
            </tbody>
          </table></div>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=freight">用這票貨詢價</a></p>
        </div>
        """
    return """
        <div class="wrap">
          <p class="kicker">Service 01</p>
          <h1>Freight</h1>
          <p class="intro">Ordinary import and export: FCL and LCL ocean, air, trucking between port or airport and warehouse, and customs paperwork. Out-of-gauge cargo is project work, storage is warehousing, and a ship in port is agency work.</p>
          <div class="split section">
            <div class="do"><h3>What this page is for</h3><p>Send the commodity, quantity, and lane to the right office. Rates, sailings, and space are confirmed per shipment.</p></div>
            <div class="dont"><h3>What this page is not</h3><p>No live tracking, no live rates, and no space guarantee. Rates and sailings come back from the office.</p></div>
          </div>
          <div class="section table-wrap"><table>
            <thead><tr><th>Mode</th><th>Fits</th><th>Prepare</th><th>Not on the site</th></tr></thead>
            <tbody>
              <tr id="ocean"><td>Ocean</td><td>FCL and LCL when the timeline can take a sailing.</td><td>Commodity, container type or volume, ports, Incoterms.</td><td>Live schedules and rates.</td></tr>
              <tr id="air"><td>Air</td><td>Time-critical cargo where volumetric weight matters.</td><td>Pieces, gross weight, dimensions.</td><td>A promise of space.</td></tr>
              <tr id="land"><td>Trucking</td><td>Moves between port, airport, warehouse, and plant.</td><td>Address, time window, height or weight limits.</td><td>A live truck position.</td></tr>
              <tr id="customs"><td>Customs</td><td>Help preparing an HS code and the paperwork for a formal entry.</td><td>Commercial invoice, packing list, any existing classification.</td><td>A duty calculator. Duty follows the customs assessment.</td></tr>
            </tbody>
          </table></div>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=freight">Enquire with this cargo</a></p>
        </div>
        """


def project(lang):
    if lang == "zh":
        return """
        <div class="wrap">
          <p class="kicker">服務 02</p>
          <h1>專案物流</h1>
          <p class="intro">給超寬、超重、高價值，或需要吊運、拆組、路權的貨物。一般整櫃與併櫃請走貨運物流。</p>
          <div class="split section">
            <div class="do"><h3>開始前要量的</h3><ul><li>長、寬、高與毛重</li><li>重心與可吊點</li><li>能否拆成可運的件</li><li>起訖、途經的橋樑或港區限制</li><li>照片或圖面</li></ul></div>
            <div class="dont"><h3>這裡不寫的</h3><p>石油天然氣、離岸、基礎建設、鐵路與再生能源是可能的貨種，不是已完成案件。沒有客戶授權與結果數字之前，本站不放案例。</p></div>
          </div>
          <section class="section panel"><h2>詢價時會發生什麼</h2><p>辦公室先看尺寸能不能進港、上路、上船，再決定海運、陸運或拆運。回覆是這票貨的安排，不是網站上的固定價目。</p></section>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=project">送出尺寸與照片說明</a></p>
        </div>
        """
    return """
        <div class="wrap">
          <p class="kicker">Service 02</p>
          <h1>Project cargo</h1>
          <p class="intro">For cargo that is too wide, too heavy, high value, or needs a lift plan, dismantling, or a road permit. Standard FCL and LCL belong under freight.</p>
          <div class="split section">
            <div class="do"><h3>Measure this first</h3><ul><li>Length, width, height, and gross weight</li><li>Center of gravity and lifting points</li><li>Whether it can be split</li><li>Origin, destination, and known bridge or port limits</li><li>Photos or drawings</li></ul></div>
            <div class="dont"><h3>What we leave out</h3><p>Oil and gas, offshore, infrastructure, rail, and renewable energy are possible cargo types, not finished jobs. This site does not publish a case study without a client release and a real result.</p></div>
          </div>
          <section class="section panel"><h2>What an enquiry does</h2><p>The office checks whether the piece can enter the port, use the road, and go on the ship, then chooses ocean, road, or a split move. The reply is for that cargo, not a rate card on the website.</p></section>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=project">Send dimensions</a></p>
        </div>
        """


def warehouse(lang):
    if lang == "zh":
        return """
        <div class="wrap">
          <p class="kicker">服務 03</p>
          <h1>倉儲物流</h1>
          <p class="intro">公開聯絡與服務頁寫的倉儲在台中港一帶：進出倉、揀貨包裝、驗貨重工，以及貨櫃與離岸設備相關作業。作業窗口是台中辦公室。</p>
          <div class="split section">
            <div class="do"><h3>可以問的作業</h3><ul><li>進倉與出倉</li><li>依訂單揀貨、包裝</li><li>驗貨、重工</li><li>貨櫃相關作業</li></ul></div>
            <div class="dont"><h3>網站上沒有的</h3><p>沒有客戶登入，也沒有即時庫存。庫存、倉租與工班要直接問 info.txg@northgo.com，以回覆為準。</p></div>
          </div>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=warehouse">問台中倉</a></p>
        </div>
        """
    return """
        <div class="wrap">
          <p class="kicker">Service 03</p>
          <h1>Warehousing</h1>
          <p class="intro">The published warehouse operation is in the Taichung Port area: inbound and outbound, pick-and-pack, inspection and rework, plus container and offshore-equipment handling. The desk is the Taichung office.</p>
          <div class="split section">
            <div class="do"><h3>Work you can ask about</h3><ul><li>Inbound and outbound</li><li>Pick-and-pack against an order</li><li>Inspection and rework</li><li>Container handling</li></ul></div>
            <div class="dont"><h3>Not on this site</h3><p>There is no customer login and no live stock. Stock, storage, and labor are confirmed by info.txg@northgo.com.</p></div>
          </div>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=warehouse">Ask Taichung</a></p>
        </div>
        """


def shipping(lang):
    if lang == "zh":
        return """
        <div class="wrap">
          <p class="kicker">服務 04</p>
          <h1>船務代理</h1>
          <p class="intro">處理船舶在港的事：靠泊窗口、船邊協調、港口文件。貨主委託的貨物進出，請走貨運或專案，不要和船代混在同一張詢價裡。</p>
          <div class="cards services section">
            <article class="card"><h3>日本港口</h3><p>東京 info.tyo@northgo.com、大阪 info.osa@northgo.com。地址在據點頁。</p></article>
            <article class="card"><h3>台灣港口</h3><p>台北總部、台中、高雄都可以作為第一個窗口，再轉到實際作業的港口。</p></article>
          </div>
          <div class="dont section"><h3>不要期待的</h3><p>這頁不是船舶動態看板，也不是船員派遣系統。需要的航次、港口與預計靠泊時間，請寫在詢價裡。</p></div>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=shipping">詢問靠港</a></p>
        </div>
        """
    return """
        <div class="wrap">
          <p class="kicker">Service 04</p>
          <h1>Shipping agency</h1>
          <p class="intro">The ship’s side of a port call: berth coordination, ship-side arrangements, and port papers. Cargo the shipper hands over is freight or project work, and should not share one enquiry with the vessel call.</p>
          <div class="cards services section">
            <article class="card"><h3>Japan</h3><p>Tokyo info.tyo@northgo.com and Osaka info.osa@northgo.com. Addresses are on the offices page.</p></article>
            <article class="card"><h3>Taiwan</h3><p>Taipei HQ, Taichung, or Kaohsiung can take the first call and pass it to the port that will do the work.</p></article>
          </div>
          <div class="dont section"><h3>Not this page</h3><p>There is no vessel-position board and no crew desk. Put the voyage, port, and expected berth time in the enquiry.</p></div>
          <p class="section"><a class="btn btn-navy" href="contact.html?service=shipping">Ask about a port call</a></p>
        </div>
        """


def scenarios(lang):
    if lang == "zh":
        head = """<p class="kicker">不是客戶案例</p><h1>服務情境</h1>
        <p class="intro">下面四則只說明哪種貨該找哪個辦公室、該準備什麼。沒有客戶名稱，也沒有節省天數或金額。那些數字要有授權與紀錄才寫得下去。</p>"""
        items = [
            ("台灣出口，美西進口", "貨運 · 海運", "高雄或台北收委託，洛杉磯辦公室作目的港窗口。", "品名、櫃型、起運港、Monterey Park 辦公室是否需要清關後的陸運。", "offices.html#lax"),
            ("台中倉進出", "倉儲", "貨進台中港倉庫，再揀貨出倉。", "進倉預告、件數、是否驗貨。庫存不要看網站。", "warehouse.html"),
            ("一件超寬設備", "專案", "先確認尺寸、吊點與路權，再決定走海運或拆運。", "三視圖或照片、毛重、能否拆解。", "project.html"),
            ("船舶靠日本港口", "船代", "東京或大阪辦公室協調靠泊，貨物另案。", "航次、港口、預計靠泊、船舶資料。", "shipping.html"),
        ]
        label_read, label_bring = "怎麼分", "請準備"
    else:
        head = """<p class="kicker">Not client stories</p><h1>Service scenarios</h1>
        <p class="intro">These four notes only say which office fits which job, and what to prepare. There are no client names and no savings in days or money. Those figures need a release and a record.</p>"""
        items = [
            ("Export from Taiwan, import on the US West Coast", "Freight · ocean", "Kaohsiung or Taipei takes the booking. Los Angeles is the destination desk.", "Commodity, container type, loading port, and whether Monterey Park should arrange trucking after customs.", "offices.html#lax"),
            ("In and out of Taichung", "Warehousing", "Cargo enters the Taichung Port warehouse and leaves as picked orders.", "Inbound notice, piece count, and whether inspection is required. Do not look up stock here.", "warehouse.html"),
            ("One oversized piece", "Project", "Confirm size, lifting points, and road limits before choosing a ship or a split move.", "Drawings or photos, gross weight, and whether it can be dismantled.", "project.html"),
            ("A ship calling Japan", "Agency", "Tokyo or Osaka coordinates the berth. The cargo is a separate job.", "Voyage, port, expected berthing, vessel details.", "shipping.html"),
        ]
        label_read, label_bring = "How it is split", "Prepare"
    cards = []
    for title, kind, body, prep, href in items:
        cards.append(f'<article class="card"><p class="kicker">{kind}</p><h3>{title}</h3><p>{body}</p><p style="margin-top:8px"><strong>{label_bring}</strong> {prep}</p><a class="more" href="{href}">{label_read}</a></article>')
    return f'<div class="wrap">{head}<div class="cards services section">{"".join(cards)}</div></div>'


def about(lang):
    if lang == "zh":
        return """
        <div class="wrap">
          <p class="kicker">About</p>
          <h1>關於 Northgo</h1>
          <p class="intro">1988 年在台北創立，名稱是 Max Seair Logistics。2024 年 11 月 11 日更名為 Northgo。總部仍在台北市民生東路三段 10 號 7 樓。</p>
          <div class="cards services section">
            <article class="card"><h3>願景</h3><p>成為客戶遇到物流問題時會再找的名字。信任要靠逐票交代，不是靠標語。</p></article>
            <article class="card"><h3>使命</h3><p>讓物流變得輕鬆：範圍講清楚，文件交得出來，窗口找得到人。</p></article>
            <article class="card"><h3>價值觀</h3><p>對客戶交代、把費用與進度說明白、作業方法可以改、減少不必要的空運與空櫃。後兩項是方向，不是已稽核的證書。</p></article>
            <article class="card"><h3>換名之後</h3><p>換的是名字。團隊與台北總部沒有在公開資料裡說自己換過地址。</p></article>
          </div>
          <div class="dont section"><h3>本站目前不宣稱的</h3><p>24 小時全年無休、360 度方案、全聯盟合約、線上即時可視。這些要有班表、證書或系統可以對，才寫得成事實。</p></div>
        </div>
        """
    return """
        <div class="wrap">
          <p class="kicker">About</p>
          <h1>About Northgo</h1>
          <p class="intro">Founded in Taipei in 1988 as Max Seair Logistics. Renamed Northgo on 11 November 2024. Headquarters is still 7F, No. 10, Section 3, Minsheng East Road, Taipei.</p>
          <div class="cards services section">
            <article class="card"><h3>Vision</h3><p>Be the name a client calls again. Trust comes from the next shipment, not from a tagline.</p></article>
            <article class="card"><h3>Mission</h3><p>Make logistics effortless by stating the scope, producing the documents, and naming a person at an office.</p></article>
            <article class="card"><h3>Values</h3><p>Accountable to the client, plain about cost and status, willing to change the method, and wary of needless air freight and empty equipment. The last two are a direction, not an audited certificate.</p></article>
            <article class="card"><h3>After the rename</h3><p>The name changed. Public pages do not say the team or the Taipei headquarters moved.</p></article>
          </div>
          <div class="dont section"><h3>Not claimed here</h3><p>Round-the-clock coverage, a 360-degree solution, a contract with every alliance, and live visibility. Those become facts only when a roster, a certificate, or a system is there to show.</p></div>
        </div>
        """


def contact(lang):
    if lang == "zh":
        title, intro = "詢價", "這張表不會送到網站伺服器。送出後會打開你的電子郵件軟體，收件人是你選的辦公室。請自行寄出。若郵件軟體沒有打開，直接寫信到下方信箱即可。"
        labels = ["姓名", "公司", "Email", "電話", "國家或地區", "服務", "起運地", "目的地", "貨量與尺寸", "其他說明"]
        keys = ["name", "company", "email", "phone", "country", "service", "origin", "destination", "cargo", "message"]
        services = [("freight", "貨運物流"), ("project", "專案物流"), ("warehouse", "倉儲物流"), ("shipping", "船務代理"), ("unsure", "還不確定")]
        ph = {"origin": "城市、港口或工廠", "destination": "城市、港口或倉庫", "cargo": "件數、毛重、尺寸或櫃型", "message": "貿易條件、希望時程、參考號"}
        req = "請填這欄"
        invalid, sent = "還有必填欄位是空的。", "郵件軟體應已打開，收件人是 {email}。請按寄出。若沒有打開，請直接寫信到這個地址。"
        subject = "Northgo 詢價"
        submit, side = "用電子郵件送出", "七個信箱"
        office_label, to_label = "辦公室", "收件人："
    else:
        title, intro = "Enquire", "This form is not posted to a server. Submit opens your email app, addressed to the office you chose. You still send the message. If no app opens, write to the address below."
        labels = ["Name", "Company", "Email", "Phone", "Country or region", "Service", "Origin", "Destination", "Quantity and size", "Anything else"]
        keys = ["name", "company", "email", "phone", "country", "service", "origin", "destination", "cargo", "message"]
        services = [("freight", "Freight"), ("project", "Project cargo"), ("warehouse", "Warehousing"), ("shipping", "Shipping agency"), ("unsure", "Not sure yet")]
        ph = {"origin": "City, port, or plant", "destination": "City, port, or warehouse", "cargo": "Pieces, gross weight, size, or container", "message": "Incoterms, timing, reference"}
        req = "Required"
        invalid, sent = "A required field is empty.", "Your email app should be open to {email}. Send it from there. If nothing opened, write to that address."
        subject = "Northgo enquiry"
        submit, side = "Open email", "Seven addresses"
        office_label, to_label = "Office", "To: "
    fields = []
    required = {"name", "email", "service", "origin", "destination", "cargo"}
    span = {"message", "cargo"}
    for key, label in zip(keys, labels):
        classes = "span-2" if key in span or key == "message" else ""
        err = f'<span class="field-error" hidden>{req}</span>' if key in required else ""
        req_attr = " required" if key in required else ""
        if key == "service":
            options = "".join(f'<option value="{value}">{html.escape(text)}</option>' for value, text in services)
            control = f'<select name="service" data-label="{html.escape(label)}" required><option value="">{req}</option>{options}</select>'
        elif key == "message":
            control = f'<textarea name="message" data-label="{html.escape(label)}" placeholder="{html.escape(ph["message"])}"></textarea>'
        else:
            input_type = "email" if key == "email" else "text"
            placeholder = f' placeholder="{html.escape(ph[key])}"' if key in ph else ""
            control = f'<input type="{input_type}" name="{key}" data-label="{html.escape(label)}"{req_attr}{placeholder}>'
        fields.append(f'<label class="{classes}">{html.escape(label)}{control}{err}</label>')
    options = []
    for office in OFFICES:
        name = office_name(office, lang)
        options.append(f'<option value="{office["id"]}" data-email="{office["email"]}">{html.escape(name)} · {office["email"]}</option>')
    office_field = f'<label class="span-2">{office_label}<select name="office" data-label="{office_label}">{"".join(options)}</select></label>'
    cards = []
    for office in OFFICES:
        cards.append(f'<p><strong>{html.escape(office_name(office, lang))}</strong><br><a href="mailto:{office["email"]}">{office["email"]}</a></p>')
    return f'''
    <div class="wrap">
      <p class="kicker">Enquiry</p>
      <h1>{title}</h1>
      <p class="intro">{intro}</p>
      <div class="contact-layout section">
        <form class="panel" data-enquiry action="mailto:info.tpe@northgo.com" method="post" enctype="text/plain" data-invalid="{html.escape(invalid)}" data-sent="{html.escape(sent)}" data-subject="{html.escape(subject)}">
          <div class="form-grid">{''.join(fields)}{office_field}
            <div class="span-2"><button class="btn btn-navy" type="submit">{submit}</button></div>
            <p class="span-2 muted" id="form-status" role="status">{to_label}<span id="office-mail">info.tpe@northgo.com</span></p>
          </div>
        </form>
        <aside class="panel"><h2>{side}</h2>{''.join(cards)}</aside>
      </div>
    </div>
    '''


def offices(lang):
    if lang == "zh":
        head = """<p class="kicker">Locations</p><h1>七個辦公室</h1>
        <p class="intro">地址、電話與信箱整理自公開聯絡頁。全球視角把洛杉磯放在太平洋同一側，才能和亞洲一起看見；點區域之後用實際經度。右下角是台灣三個辦公室。</p>"""
        regions = [("world", "全球"), ("east", "東亞"), ("taiwan", "台灣"), ("japan", "日本"), ("sea", "東南亞"), ("na", "北美")]
        caption = "地圖圖磚來自 OpenStreetMap。點列表上的辦公室會拉近並打開地址。"
        inset = "台灣辦公室放大"
    else:
        head = """<p class="kicker">Locations</p><h1>Seven offices</h1>
        <p class="intro">Addresses, phones, and mailboxes come from the public contact page. The world view places Los Angeles on the Pacific side so it sits with Asia; regional views use the real longitude. The corner map is the three Taiwan offices.</p>"""
        regions = [("world", "World"), ("east", "East Asia"), ("taiwan", "Taiwan"), ("japan", "Japan"), ("sea", "Southeast Asia"), ("na", "North America")]
        caption = "Tiles from OpenStreetMap. Choose an office in the list to zoom in and open the address."
        inset = "Taiwan offices"
    buttons = "".join(
        f'<button type="button" data-region="{rid}" aria-pressed="{"true" if rid=="world" else "false"}">{html.escape(label)}</button>'
        for rid, label in regions
    )
    cards = []
    payload = []
    for office in OFFICES:
        name = office_name(office, lang)
        address = office["address_zh"] if lang == "zh" else office["address_en"]
        other = office["address_en"] if lang == "zh" else office["address_zh"]
        fax = f'<br>Fax {office["fax"]}' if office["fax"] else ""
        cards.append(
            f'<article class="card office-card" id="{office["id"]}"><h3>{html.escape(name)}</h3>'
            f'<p>{html.escape(address)}</p><p class="muted">{html.escape(other)}</p>'
            f'<p><a href="tel:{office["phone"]}">{office["phone"]}</a>{fax}<br><a href="mailto:{office["email"]}">{office["email"]}</a></p>'
            f'<button type="button" class="btn btn-secondary" data-office="{office["id"]}" style="margin-top:8px">{"在地圖上打開" if lang=="zh" else "Show on the map"}</button></article>'
        )
        payload.append({
            "id": office["id"], "region": office["region"], "hq": office["hq"],
            "lat": office["lat"], "lng": office["lng"], "name": name,
            "short": office["short_zh"] if lang == "zh" else office["short_en"],
            "address": address, "addressEn": other,
            "phone": office["phone"], "fax": office["fax"], "email": office["email"],
        })
    data = json.dumps(payload, ensure_ascii=False)
    return f'''
    <div class="wrap">
      {head}
      <div class="map-layout section">
        <div>
          <div class="regions" style="margin-bottom:10px">{buttons}</div>
          <div class="stage"><div id="map" role="region" aria-label="{inset}"></div><div id="inset" aria-label="{inset}"></div></div>
          <p class="muted" style="margin-top:8px">{caption}</p>
        </div>
        <div class="cards">{''.join(cards)}</div>
      </div>
    </div>
    <script type="application/json" id="office-data">{data}</script>
    '''


def legal(lang):
    if lang == "zh":
        blocks = [
            ("privacy", "隱私", "詢價表單不會把資料存進這個預覽站。按送出只會打開你自己的電子郵件軟體。正式網站如何蒐集、保存與跨境傳輸個人資料，以 <a href=\"https://www.northgo.com/zh-tw/legal/privacy-policy\">官網隱私權政策</a> 為準。"),
            ("terms", "使用條款", "預覽站的服務說明用來討論重建，不構成報價、艙位或倉位承諾。正式服務條款見 <a href=\"https://www.northgo.com/zh-tw/legal/terms\">官網條款</a>。"),
            ("cookies", "Cookie", "這份預覽站自己不安裝分析或廣告 Cookie。打開據點地圖時，瀏覽器會向 OpenStreetMap 的圖磚伺服器要圖片，該請求適用對方的政策。正式站的 Cookie 說明見 <a href=\"https://www.northgo.com/zh-tw/legal/cookie-policy\">官網 Cookie 政策</a>。"),
            ("disclaimer", "聲明", "辦公室地址、電話與信箱整理自 2026-11-25 的公開聯絡頁。若與最新資料不同，以 <a href=\"https://www.northgo.com/zh-tw/contact\">官網聯絡頁</a> 為準。"),
        ]
        title, lede = "法律說明", "這是預覽站的說明，不是把官網法律頁整份抄過來。具約束力的文本在正式網站。"
    else:
        blocks = [
            ("privacy", "Privacy", "The enquiry form does not store data on this preview. Submit only opens your own email app. How the live site collects, keeps, and transfers personal data is governed by its <a href=\"https://www.northgo.com/legal/privacy-policy\">privacy policy</a>."),
            ("terms", "Terms", "Service descriptions here are for the rebuild discussion. They are not a rate, a booking, or space. The live <a href=\"https://www.northgo.com/legal/terms\">terms</a> govern the operating company."),
            ("cookies", "Cookies", "This preview sets no analytics or advertising cookies. Opening the office map asks OpenStreetMap for tiles, under that service’s policy. The live <a href=\"https://www.northgo.com/legal/cookie-policy\">cookie policy</a> covers the production site."),
            ("disclaimer", "Disclaimer", "Offices, phones, and mailboxes were taken from the public contact page on 2026-11-25. If they differ from the latest notice, the <a href=\"https://www.northgo.com/contact\">live contact page</a> wins."),
        ]
        title, lede = "Legal notes", "Notes for this preview, not a copy of the live legal pages. The binding text stays on the production site."
    parts = [f'<section class="section panel" id="{sid}"><h2>{heading}</h2><p>{body}</p></section>' for sid, heading, body in blocks]
    return f'<div class="wrap"><p class="kicker">Legal</p><h1>{title}</h1><p class="intro">{lede}</p>{"".join(parts)}</div>'


BUILDERS = {
    "index": home,
    "freight": freight,
    "project": project,
    "warehouse": warehouse,
    "shipping": shipping,
    "scenarios": scenarios,
    "about": about,
    "contact": contact,
    "offices": offices,
    "legal": legal,
}

META = {
    "zh": {
        "index": ("Northgo｜讓物流變得輕鬆", "台北總部的物流公司。貨運、專案貨、倉儲與船代，辦公室在台灣、日本、越南與美國。此預覽站不提供線上追蹤。"),
        "freight": ("貨運物流｜Northgo", "海運整櫃與併櫃、空運、陸運與報關。沒有即時運價與貨況查詢。"),
        "project": ("專案物流｜Northgo", "超寬、超重與需要吊運的貨物。先準備尺寸、重量與吊點。"),
        "warehouse": ("倉儲物流｜Northgo", "台中港倉儲的進出倉、揀貨與驗貨。網站不顯示庫存。"),
        "shipping": ("船務代理｜Northgo", "船舶靠港的協調與港口文件。東京、大阪與台灣辦公室可作為窗口。"),
        "scenarios": ("服務情境｜Northgo", "四種作業怎麼對到辦公室。不是客戶案例，沒有績效數字。"),
        "about": ("關於 Northgo", "1988 年於台北創立，2024 年 11 月 11 日由 Max Seair Logistics 更名為 Northgo。"),
        "contact": ("詢價｜Northgo", "把服務、起訖與貨量寄到選定的辦公室信箱。表單不會存進網站。"),
        "offices": ("全球辦公室｜Northgo", "台北、台中、高雄、東京、大阪、胡志明市與洛杉磯的地址、電話與信箱。"),
        "legal": ("法律說明｜Northgo", "預覽站的隱私、條款、Cookie 與聲明。正式文本以官網為準。"),
    },
    "en": {
        "index": ("Northgo | Making logistics effortless", "A Taipei logistics company: freight, project cargo, warehousing, and shipping agency, with offices in Taiwan, Japan, Vietnam, and the United States. This preview has no tracking."),
        "freight": ("Freight | Northgo", "FCL, LCL, air, trucking, and customs paperwork. No live rates or tracking."),
        "project": ("Project cargo | Northgo", "Wide, heavy, and lifted cargo. Start with dimensions, weight, and lifting points."),
        "warehouse": ("Warehousing | Northgo", "Taichung Port inbound, outbound, pick-and-pack, and inspection. No stock on the site."),
        "shipping": ("Shipping agency | Northgo", "Port-call coordination and papers. Tokyo, Osaka, and the Taiwan offices can take the first call."),
        "scenarios": ("Scenarios | Northgo", "Four jobs matched to offices. Not client stories, and no performance figures."),
        "about": ("About Northgo", "Founded in Taipei in 1988. Renamed from Max Seair Logistics to Northgo on 11 November 2024."),
        "contact": ("Enquire | Northgo", "Send the service, lane, and quantity to the office you choose. The form is not stored on the site."),
        "offices": ("Offices | Northgo", "Addresses, phones, and mailboxes in Taipei, Taichung, Kaohsiung, Tokyo, Osaka, Ho Chi Minh City, and Los Angeles."),
        "legal": ("Legal notes | Northgo", "Privacy, terms, cookies, and a disclaimer for this preview. The live site holds the binding text."),
    },
}


def file_name(slug):
    return "index.html" if slug == "index" else f"{slug}.html"


def render(lang, slug):
    ui = UI[lang]
    title, description = META[lang][slug]
    prefix = "" if lang == "zh" else "../"
    other = f"en/{file_name(slug)}" if lang == "zh" else f"../{file_name(slug)}"
    services = [("freight", ui["freight"]), ("project", ui["project"]), ("warehouse", ui["warehouse"]), ("shipping", ui["shipping"])]
    service_links = []
    for sid, label in services:
        current = ' aria-current="page"' if sid == slug else ""
        service_links.append(f'<a href="{file_name(sid)}"{current}>{label}</a>')
    def link(sid, label):
        current = ' aria-current="page"' if sid == slug else ""
        return f'<a href="{file_name(sid)}"{current}>{label}</a>'
    nav = f'''
    <div class="menu">
      <button class="menu-btn" type="button" aria-expanded="false">{ui["services"]}</button>
      <div class="menu-panel">{''.join(service_links)}</div>
    </div>
    {link("offices", ui["offices"])}
    {link("scenarios", ui["scenarios"])}
    {link("about", ui["about"])}
    <a class="lang" href="{other}" hreflang="{'en' if lang=='zh' else 'zh-Hant'}">{ui["other"]}</a>
    <a class="btn btn-navy" href="{file_name("contact")}">{ui["enquire"]}</a>
    '''
    leaflet_css = leaflet_js = ""
    if slug == "offices":
        leaflet_css = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">'
        leaflet_js = '<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>'
    org = ""
    if slug == "index":
        org = """<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Northgo","url":"https://www.northgo.com/","foundingDate":"1988","email":"info.tpe@northgo.com","telephone":"+886-2-2531-8677","address":{"@type":"PostalAddress","streetAddress":"7F., No. 10, Sec. 3, Minsheng E. Rd.","addressLocality":"Taipei","postalCode":"104511","addressCountry":"TW"}}</script>"""
    body = BUILDERS[slug](lang)
    return f'''<!DOCTYPE html>
<html lang="{ui["lang"]}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="alternate" hreflang="zh-Hant" href="{prefix if lang=='en' else ''}{file_name(slug) if lang=='en' else file_name(slug)}">
  <link rel="alternate" hreflang="en" href="{'en/' if lang=='zh' else ''}{file_name(slug)}">
  <link rel="stylesheet" href="{prefix}styles.css">
  {leaflet_css}
  {org}
</head>
<body>
  <a class="skip" href="#main">{ui["skip"]}</a>
  <header class="site-header"><div class="wrap bar">
    <a class="logo" href="{file_name("index")}">North<span>go</span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">{ui["menu"]}</button>
    <nav id="site-nav">{nav}</nav>
  </div></header>
  <main id="main">{body}</main>
  <footer><div class="wrap foot">
    <nav>
      <a href="legal.html#privacy">{ui["privacy"]}</a>
      <a href="legal.html#terms">{ui["terms"]}</a>
      <a href="legal.html#cookies">{ui["cookies"]}</a>
      <a href="legal.html#disclaimer">{ui["disclaimer"]}</a>
      <a href="https://www.northgo.com/">www.northgo.com</a>
    </nav>
    <p>{ui["foot"]}</p>
  </div></footer>
  {leaflet_js}
  <script src="{prefix}site.js"></script>
</body>
</html>
'''


def main():
    en_dir = ROOT / "en"
    en_dir.mkdir(exist_ok=True)
    for slug in BUILDERS:
        (ROOT / file_name(slug)).write_text(render("zh", slug), encoding="utf-8")
        (en_dir / file_name(slug)).write_text(render("en", slug), encoding="utf-8")
    print(f"wrote {len(BUILDERS) * 2} pages")


if __name__ == "__main__":
    main()
