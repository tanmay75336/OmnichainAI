export default function SectionCard({
  title,
  subtitle,
  aside,
  className = '',
  children,
}) {
  return (
    <section className={`section-card ${className}`.trim()}>
      <header className="section-card__header">
        <div>
          <p className="section-card__eyebrow">{subtitle}</p>
          <h2 className="section-card__title">{title}</h2>
        </div>
        {aside ? <div className="section-card__aside">{aside}</div> : null}
      </header>
      <div className="section-card__body">{children}</div>
    </section>
  )
}
