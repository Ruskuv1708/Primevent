import { useMemo, useState } from "react";

const copy = {
  en: {
    nav: ["Programs", "Prices", "Production", "Contact"],
    heroTitle: "Prime Kids Tashkent",
    heroSubhead:
      "Animator teams, scripted shows, quests, characters, costumes, and joyful celebrations made especially for children.",
    primaryCta: "Book a Program",
    secondaryCta: "See Formats",
    heroFacts: [
      { value: "120+", label: "happy celebrations" },
      { value: "24/7", label: "booking support" },
      { value: "200+", label: "costumes and props" },
    ],
    showPanelTitle: "This week",
    showPanelItems: [
      { time: "Sat 12:00", title: "Kids Galaxy Show", meta: "Animator team + quest" },
      { time: "Sun 17:30", title: "Royal Masquerade", meta: "Hosts, music, costumes" },
      { time: "Thu 19:00", title: "Corporate Team Quest", meta: "Indoor or outdoor" },
    ],
    programsTitle: "Programs built for the room",
    programsIntro:
      "Choose a proven format or ask us to combine characters, music, competitions, and production into one custom scenario.",
    programs: [
      {
        title: "Kids parties",
        meta: "Birthdays, schools, family venues",
        copy: "Animators, character arrivals, mini quests, bubble shows, music blocks, and photo moments.",
      },
      {
        title: "Quest shows",
        meta: "Ages 6-16",
        copy: "Scripted missions with teams, clues, hosts, props, prizes, and a clear finale.",
      },
      {
        title: "Corporate events",
        meta: "Teams, retail, offices",
        copy: "Team building, MC programs, launch activations, branded games, and staff celebrations.",
      },
      {
        title: "Graduations",
        meta: "Kindergarten, school, university",
        copy: "A complete run of show with hosts, games, dance moments, costumes, and parent-friendly timing.",
      },
    ],
    pricingTitle: "Programs and prices",
    pricingIntro:
      "Choose a ready-made service or combine several formats into one celebration. Prices are shown in Uzbek soums.",
    pricingNote: "Final cost depends on the venue, date, team size, and selected scenario.",
    pricingGroups: [
      {
        title: "Animation program",
        items: [
          { name: "Main program", details: "2 characters · 1 hour · music and an engaging scenario", price: "950,000 UZS" },
        ],
      },
      {
        title: "Additional services",
        items: [
          { name: "Additional character", details: "One more character for the selected program", price: "200,000 UZS" },
          { name: "Atmosphere entertainment", details: "1 entertainer · 1 hour", price: "500,000 UZS" },
        ],
      },
      {
        title: "Show programs",
        items: [
          { name: "Chemistry show", details: "Spectacular experiments", price: "900,000 UZS" },
          { name: "Paper party", details: "Kilograms of soft paper", price: "1,200,000 UZS" },
          { name: "Foil show", details: "Shimmering foil performance", price: "1,200,000 UZS" },
          { name: "Ribbon show", details: "Thousands of satin ribbons · bright photos · 1 hour", price: "1,000,000 UZS" },
          { name: "Magic show", details: "Interactive illusion performance", price: "from 1,500,000 UZS" },
        ],
      },
      {
        title: "Creativity and intelligence",
        items: [
          { name: "Twisting", details: "1 entertainer · 1 hour", price: "500,000 UZS" },
          { name: "Face painting", details: "Professional paints · 1 hour", price: "400,000 UZS" },
          { name: "Quiz show", details: "Interactive format", price: "from 1,000,000 UZS" },
          { name: "Workshops", details: "Various themes", price: "from 1,000,000 UZS" },
        ],
      },
    ],
    productionTitle: "Full-cycle production, not only performers",
    production: [
      "Program selection by age, venue, audience size, and timing",
      "Hosts, animators, costumes, props, music, and stage flow",
      "Fast coordination through phone or Telegram before the event",
    ],
    productionSteps: ["Scenario", "Team", "Showtime"],
    contactTitle: "Tell us the date and audience",
    contactCopy:
      "Call or message us on Telegram or Instagram. We will suggest the right program, team size, and budget range.",
  },
  ru: {
    nav: ["Программы", "Цены", "Продакшн", "Контакты"],
    heroTitle: "Prime Kids Tashkent",
    heroSubhead:
      "Аниматоры, шоу, квесты, персонажи, костюмы и праздники под ключ — всё для ярких детских событий.",
    primaryCta: "Заказать программу",
    secondaryCta: "Смотреть форматы",
    heroFacts: [
      { value: "120+", label: "ярких праздников" },
      { value: "24/7", label: "принимаем заявки" },
      { value: "200+", label: "костюмов и реквизита" },
    ],
    showPanelTitle: "Ближайшие форматы",
    showPanelItems: [
      { time: "Сб 12:00", title: "Kids Galaxy Show", meta: "Аниматоры + квест" },
      { time: "Вс 17:30", title: "Royal Masquerade", meta: "Ведущие, музыка, костюмы" },
      { time: "Чт 19:00", title: "Corporate Team Quest", meta: "В помещении или на улице" },
    ],
    programsTitle: "Программы под ваш формат",
    programsIntro:
      "Выберите готовое направление или соберем сценарий из персонажей, музыки, конкурсов и продакшна.",
    programs: [
      {
        title: "Детские праздники",
        meta: "Дни рождения, школы, семейные площадки",
        copy: "Аниматоры, выходы персонажей, мини-квесты, шоу мыльных пузырей, музыка и фото-моменты.",
      },
      {
        title: "Квест-шоу",
        meta: "Возраст 6-16",
        copy: "Сюжетные миссии с командами, подсказками, ведущими, реквизитом, призами и финалом.",
      },
      {
        title: "Корпоративы",
        meta: "Команды, ритейл, офисы",
        copy: "Тимбилдинги, ведущие, промо-активации, брендированные игры и праздники для сотрудников.",
      },
      {
        title: "Выпускные",
        meta: "Садик, школа, университет",
        copy: "Готовый тайминг с ведущими, играми, танцевальными блоками, костюмами и понятной координацией.",
      },
    ],
    pricingTitle: "Программы и цены",
    pricingIntro:
      "Выберите готовую услугу или соберите праздник из нескольких форматов. Все цены указаны в сумах.",
    pricingNote: "Итоговая стоимость зависит от площадки, даты, состава команды и выбранного сценария.",
    pricingGroups: [
      {
        title: "Анимационная программа",
        items: [
          { name: "Основная программа", details: "2 героя · 1 час · музыкальное сопровождение и увлекательный сценарий", price: "950 000 сум" },
        ],
      },
      {
        title: "Дополнительные услуги",
        items: [
          { name: "Дополнительный герой", details: "Ещё один персонаж к выбранной программе", price: "200 000 сум" },
          { name: "Атмосферная работа", details: "1 аниматор · 1 час", price: "500 000 сум" },
        ],
      },
      {
        title: "Шоу-программы",
        items: [
          { name: "Химическое шоу", details: "Зрелищные эксперименты", price: "900 000 сум" },
          { name: "Бумажный драйв", details: "Килограммы мягкой бумаги", price: "1 200 000 сум" },
          { name: "Фольга-шоу", details: "Яркое шоу с блестящей фольгой", price: "1 200 000 сум" },
          { name: "Ленточное шоу", details: "Тысячи атласных лент · яркие фотографии · 1 час", price: "1 000 000 сум" },
          { name: "Иллюзионное шоу", details: "Интерактивное представление с фокусами", price: "от 1 500 000 сум" },
        ],
      },
      {
        title: "Творчество и интеллект",
        items: [
          { name: "Твистинг", details: "1 аниматор · 1 час", price: "500 000 сум" },
          { name: "Аквагрим", details: "Профессиональные краски · 1 час", price: "400 000 сум" },
          { name: "Квиз-шоу", details: "Интерактивный формат", price: "от 1 000 000 сум" },
          { name: "Мастер-классы", details: "Различные тематики", price: "от 1 000 000 сум" },
        ],
      },
    ],
    productionTitle: "Праздник под ключ, а не только артисты",
    production: [
      "Подбор программы по возрасту, площадке, числу гостей и таймингу",
      "Ведущие, аниматоры, костюмы, реквизит, музыка и ход события",
      "Быстрая координация по телефону или в Telegram перед праздником",
    ],
    productionSteps: ["Сценарий", "Команда", "Шоу"],
    contactTitle: "Расскажите дату и аудиторию",
    contactCopy:
      "Позвоните или напишите в Telegram или Instagram. Мы предложим формат, состав команды и ориентир по бюджету.",
  },
};

const seoLinks = [
  { href: "/animatory-tashkent/", label: "Аниматоры в Ташкенте" },
  { href: "/detskie-prazdniki-tashkent/", label: "Детские праздники" },
  { href: "/shou-programmy-tashkent/", label: "Шоу-программы" },
  { href: "/kvesty-tashkent/", label: "Квесты" },
  { href: "/vypusknye-tashkent/", label: "Выпускные" },
  { href: "/timbildingi-tashkent/", label: "Тимбилдинги" },
];

export default function App() {
  const [language, setLanguage] = useState("ru");
  const current = copy[language];

  const year = useMemo(() => new Date().getFullYear(), []);

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="prime-site">
      <header className="site-header">
        <button className="brand-lockup" type="button" onClick={() => scrollTo("top")}>
          <img src="/prime-kids-logo.jpg" alt="" />
          <span>Prime Kids</span>
        </button>
        <nav className="site-nav" aria-label="Main navigation">
          <button type="button" onClick={() => scrollTo("programs")}>{current.nav[0]}</button>
          <button type="button" onClick={() => scrollTo("pricing")}>{current.nav[1]}</button>
          <button type="button" onClick={() => scrollTo("production")}>{current.nav[2]}</button>
          <button type="button" onClick={() => scrollTo("contact")}>{current.nav[3]}</button>
        </nav>
        <div className="language-toggle" role="group" aria-label="Language toggle">
          <button
            type="button"
            className={language === "en" ? "lang-button active" : "lang-button"}
            onClick={() => setLanguage("en")}
          >
            EN
          </button>
          <button
            type="button"
            className={language === "ru" ? "lang-button active" : "lang-button"}
            onClick={() => setLanguage("ru")}
          >
            RU
          </button>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <h1 id="hero-title">{current.heroTitle}</h1>
            <p className="hero-subhead">{current.heroSubhead}</p>
            <div className="hero-actions">
              <button className="primary" type="button" onClick={() => scrollTo("contact")}>
                {current.primaryCta}
              </button>
              <button className="secondary" type="button" onClick={() => scrollTo("programs")}>
                {current.secondaryCta}
              </button>
            </div>
          </div>

          <div className="hero-stage" aria-label="Prime Kids show board">
            <div className="logo-orbit">
              <img src="/prime-kids-logo.jpg" alt="Prime Kids" />
            </div>
            <div className="show-panel">
              <div className="show-panel-head">
                <span>{current.showPanelTitle}</span>
                <strong>{year}</strong>
              </div>
              <div className="show-list">
                {current.showPanelItems.map((item) => (
                  <div className="show-row" key={item.title}>
                    <span>{item.time}</span>
                    <div>
                      <strong>{item.title}</strong>
                      <small>{item.meta}</small>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="fact-strip" aria-label="Prime Kids facts">
          {current.heroFacts.map((fact) => (
            <div className="fact" key={fact.label}>
              <strong>{fact.value}</strong>
              <span>{fact.label}</span>
            </div>
          ))}
        </section>

        <section className="programs" id="programs">
          <div className="section-heading">
            <h2>{current.programsTitle}</h2>
            <p>{current.programsIntro}</p>
          </div>
          <div className="program-grid">
            {current.programs.map((program, index) => (
              <article className="program-card" key={program.title}>
                <span className="program-index">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h3>{program.title}</h3>
                  <p className="program-meta">{program.meta}</p>
                  <p>{program.copy}</p>
                </div>
              </article>
            ))}
          </div>
          <nav className="seo-link-grid" aria-label="Популярные услуги Prime Kids">
            {seoLinks.map((link) => (
              <a href={link.href} key={link.href}>
                {link.label}
              </a>
            ))}
          </nav>
        </section>

        <section className="pricing" id="pricing">
          <div className="section-heading pricing-heading">
            <h2>{current.pricingTitle}</h2>
            <p>{current.pricingIntro}</p>
          </div>
          <div className="pricing-grid">
            {current.pricingGroups.map((group, groupIndex) => (
              <article className={`price-group price-group--${groupIndex + 1}`} key={group.title}>
                <h3>{group.title}</h3>
                <div className="price-list">
                  {group.items.map((item) => (
                    <div className="price-row" key={item.name}>
                      <div>
                        <strong>{item.name}</strong>
                        <span>{item.details}</span>
                      </div>
                      <b>{item.price}</b>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
          <p className="pricing-note">{current.pricingNote}</p>
        </section>

        <section className="production" id="production">
          <div className="production-copy">
            <h2>{current.productionTitle}</h2>
            <ul>
              {current.production.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="production-board" aria-hidden="true">
            {current.productionSteps.map((step, index) => (
              <div className="board-line" key={step}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <strong>{step}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="contact-section contact-section--compact" id="contact">
          <div className="contact-copy">
            <h2>{current.contactTitle}</h2>
            <p>{current.contactCopy}</p>
            <div className="contact-links" aria-label={language === "ru" ? "Контакты Prime Kids" : "Prime Kids contacts"}>
              <a href="tel:+998938819222">+998 93 881 92 22</a>
              <a href="https://t.me/Prime_event_kids" target="_blank" rel="noreferrer">Telegram</a>
              <a href="https://www.instagram.com/primekids.uz" target="_blank" rel="noreferrer">@primekids.uz</a>
            </div>
          </div>

        </section>
      </main>
    </div>
  );
}
