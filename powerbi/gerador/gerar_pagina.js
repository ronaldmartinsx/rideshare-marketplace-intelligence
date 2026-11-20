// Gerador da página única com raias (ADR 0019), revisão 6 (textos por medida, ADR 0023; raia 5 na revisão 5).
// Escreve os visuais, o page.json, o tema e os registros do report.json a partir do contrato em
// _brief/report-spec.md. Não mexe no modelo semântico (medidas ficam no TMDL).
//
// Uso (na raiz do repositório):
//   LINKEDIN="https://www.linkedin.com/in/ronaldmartinsx/" \
//   node powerbi/gerador/gerar_pagina.js "powerbi/rideshare-marketplace/Rideshare Marketplace Intelligence.Report" [ActualSize|FitToPage]
//
// ATENÇÃO: o gerador APAGA e recria todos os visuais da página. Depois que o Ronald salvar ajustes
// feitos à mão no Desktop, não rodar de novo sem antes trazer esses ajustes para cá; editar o PBIR
// pontualmente. FitToPage serve só para a captura de validação da página inteira.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const reportDir = process.argv[2];
const DISPLAY = process.argv[3] || 'ActualSize';
const PAGE = '5b8ff5507780d35cb750';
const pageDir = path.join(reportDir, 'definition', 'pages', PAGE);
const visualsDir = path.join(pageDir, 'visuals');
const rrDir = path.join(reportDir, 'StaticResources', 'RegisteredResources');
const VSCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json';
const MAPA = 'zonas_tlc2877948461527192.json';
const ILUSTRACAO = 'mapa_zonas_cabecalho17624082913.svg';
const TEMA = 'RideshareTema-3f9c2a71.json';
const HTMLVIS = 'htmlContent443BE3AD55E043BF878BED274D3A6865'; // HTML Content (edição Secure), GUID gravado pelo Desktop
const LINKS = { github: 'https://github.com/ronaldmartinsx', portfolio: 'https://www.rmartinsdev.com.br/', linkedin: process.env.LINKEDIN || null };

// ---------- grade: 12 colunas x 59 linhas; margem 48; gutter 24 ----------
// revisão 5: a raia 5 começa na linha 49 e é posicionada em px (compacta, sem o vazio entre a abertura e os
// cartões); o rodapé fica logo abaixo dela (página de 5000 para 5944 px)
const FOOTER_Y = 5784;
const W = 1440, PAGE_H = FOOTER_Y + 160, COL = 114, ROW = 100, M = 48, G = 24;
const snap = v => Math.round(v / 8) * 8;
function box([c0, r0, c1, r1], slot, of) {
  let x = M + (c0 - 1) * COL, y = M + (r0 - 1) * ROW;
  let w = (c1 - c0) * COL - G, h = (r1 - r0) * ROW - G;
  if (slot) { const sw = (w + G) / of; x += (slot - 1) * sw; w = sw - G; }
  return { x: snap(x), y: snap(y), width: snap(w), height: snap(h) };
}
// faixa de borda a borda cobrindo as linhas r0..r1 (inclui o gutter acima e abaixo)
const bleed = (r0, r1, top = null) => {
  const y = top !== null ? top : snap(M + (r0 - 1) * ROW - G / 2);
  const yEnd = snap(M + (r1 - 1) * ROW - G / 2);
  return { x: 0, y, width: W, height: yEnd - y };
};

// ---------- helpers ----------
const lit = v => ({ expr: { Literal: { Value: v } } });
const str = s => lit(`'${s.replace(/'/g, "''")}'`);
const col = (t, c) => ({ Column: { Expression: { SourceRef: { Entity: t } }, Property: c } });
const mea = (t, m) => ({ Measure: { Expression: { SourceRef: { Entity: t } }, Property: m } });
const proj = (f, displayName) => {
  const k = f.Column ? 'Column' : 'Measure';
  const o = { field: f, queryRef: `${f[k].Expression.SourceRef.Entity}.${f[k].Property}`, nativeQueryRef: f[k].Property };
  if (displayName) o.displayName = displayName;
  return o;
};
const qref = f => { const k = f.Column ? 'Column' : 'Measure'; return `${f[k].Expression.SourceRef.Entity}.${f[k].Property}`; };
const fill = hex => ({ solid: { color: str(hex) } });
const fid = () => 'Filter' + crypto.randomBytes(12).toString('hex');
const srcRef = (f, a) => { const k = f.Column ? 'Column' : 'Measure'; return { [k]: { Expression: { SourceRef: { Source: a } }, Property: f[k].Property } }; };
const entOf = f => (f.Column || f.Measure).Expression.SourceRef.Entity;
function fIn(f, values) {
  return { name: fid(), field: f, type: 'Categorical', howCreated: 'User', filter: { Version: 2, From: [{ Name: 'a', Entity: entOf(f), Type: 0 }],
    Where: [{ Condition: { In: { Expressions: [srcRef(f, 'a')], Values: values.map(v => [{ Literal: { Value: `'${v}'` } }]) } } }] } };
}
function fCmp(f, kind, value) {
  return { name: fid(), field: f, type: 'Advanced', howCreated: 'User', filter: { Version: 2, From: [{ Name: 'a', Entity: entOf(f), Type: 0 }],
    Where: [{ Condition: { Comparison: { ComparisonKind: kind, Left: srcRef(f, 'a'), Right: { Literal: { Value: value } } } } }] } };
}
function fTopN(f, n, aggTable, aggCol) {
  return { name: fid(), field: f, type: 'TopN', howCreated: 'User', filter: { Version: 2,
    From: [{ Name: 'subquery', Type: 2, Expression: { Subquery: { Query: { Version: 2,
      From: [{ Name: 'b', Entity: entOf(f), Type: 0 }, { Name: 'c', Entity: aggTable, Type: 0 }],
      Select: [{ Column: { Expression: { SourceRef: { Source: 'b' } }, Property: f.Column.Property }, Name: 'field' }],
      OrderBy: [{ Direction: 2, Expression: { Aggregation: { Expression: { Column: { Expression: { SourceRef: { Source: 'c' } }, Property: aggCol } }, Function: 0 } } }],
      Top: n } } } }, { Name: 'a', Entity: entOf(f), Type: 0 }],
    Where: [{ Condition: { In: { Expressions: [srcRef(f, 'a')], Table: { SourceRef: { Source: 'subquery' } } } } }] } };
}

// ---------- estilo: uma fonte só (Segoe UI) ----------
const FONT = 'Segoe UI';
const C = { texto: '#1F1F1F', sub: '#605E5C', borda: '#E1DFDD', fundo: '#F7F7F5', navy: '#1B2A41', navyTxt: '#C9D6E8',
  p90: '#D55E00', p90t: '#FBE3D3', eco: '#0072B2', repasse: '#56B4E9', cbd: '#009E73', cbdt: '#D6F0E8', lyft: '#CC79A7', lyftt: '#F3E1EC', uber: '#4D4D4D' };
// revisão 5: índigo na raia 5 (as cores livres da paleta ficavam perto das raias 1 e 2, ou sem contraste)
const LANE = { 1: '#B04A00', 2: '#005A8C', 3: '#00785A', 4: '#9E4F80', 5: '#4B5D99' };   // faixas (texto branco com contraste AA)
const TINT = { 1: '#FBF1EA', 2: '#EAF2F8', 3: '#E8F4EF', 4: '#F6ECF2', 5: '#ECEEF6' };   // fundo levemente tingido da raia
const BASELINE = '#9AA5B1'; // revisão 5: o palpite sazonal sempre em cinza (é a régua, não o protagonista)
const run = (value, size, color, bold = false) => ({ value, textStyle: Object.assign({ fontFamily: FONT, fontSize: `${size}px`, color }, bold ? { fontWeight: 'bold' } : {}) });
const noChrome = () => ({
  background: [{ properties: { show: lit('false') } }], border: [{ properties: { show: lit('false') } }],
  padding: [{ properties: { top: lit('0D'), bottom: lit('0D'), left: lit('0D'), right: lit('0D') } }],
  title: [{ properties: { show: lit('false') } }], visualHeader: [{ properties: { show: lit('false') } }],
});
function cardVCO(title, subtitle, alt) {
  const v = {
    background: [{ properties: { show: lit('true'), color: fill('#FFFFFF'), transparency: lit('0D') } }],
    border: [{ properties: { show: lit('true'), color: fill(C.borda), radius: lit('8D') } }],
    padding: [{ properties: { top: lit('12D'), bottom: lit('12D'), left: lit('16D'), right: lit('16D') } }],
    general: [{ properties: { altText: str(alt) } }],
    title: [{ properties: { show: lit('true'), text: str(title), fontFamily: str(FONT), fontSize: lit('13D'), bold: lit('true'), fontColor: fill(C.texto) } }],
    // revisão 6 (ADR 0023): o subtítulo pode ser uma medida de texto (mea(...)), no formato que o Desktop grava
    // quando o "fx" do subtítulo aponta para um campo; texto literal só para definição, nunca para resultado
    subTitle: subtitle
      ? [{ properties: { show: lit('true'), text: subtitle.Measure ? { expr: subtitle } : str(subtitle), fontFamily: str(FONT), fontSize: lit('11D'), fontColor: fill(C.sub) } }]
      : [{ properties: { show: lit('false') } }],
  };
  return v;
}

// ---------- visuais ----------
const visuals = [];
let z = 1000;
const LANE_SHIFT = 64; // revisão 4: visuais da raia sobem 64 px (24 px da abertura; respiro maior antes da próxima raia)
const alto = reg => { const b = box(reg); return { ...b, height: b.height + LANE_SHIFT }; }; // raia 1: os 64 px vão para os visuais, a nota fica logo abaixo
function add(id, lane, pos, visual, filters) {
  const name = crypto.createHash('sha1').update(id).digest('hex').slice(0, 20);
  const position = { ...(Array.isArray(pos) ? box(pos) : pos) };
  if (typeof lane === 'number' && lane >= 1 && !/_(head|num|line|note)$/.test(id)) position.y -= LANE_SHIFT;
  const json = { $schema: VSCHEMA, name, position: { ...position, z, tabOrder: z }, visual };
  if (filters && filters.length) json.filterConfig = { filters };
  z += 1000;
  visuals.push({ id, lane, name, json });
}
const textbox = (paragraphs, chrome) => ({ visualType: 'textbox', objects: { general: [{ properties: { paragraphs } }] }, visualContainerObjects: chrome || noChrome() });
const shape = (color) => ({ visualType: 'shape',
  objects: { shape: [{ properties: { tileShape: str('rectangle') }, selector: { id: 'default' } }],
    fill: [{ properties: { show: lit('true'), fillColor: fill(color), transparency: lit('0D') }, selector: { id: 'default' } }],
    // revisão 6: o contorno vai em DUAS entradas, como o Desktop grava; só a com seletor é ignorada e a borda
    // aparece (na revisão 5, o Desktop acrescentou a entrada sem seletor ao salvar, e a regeneração a apagou)
    outline: [{ properties: { show: lit('false') }, selector: { id: 'default' } }, { properties: { show: lit('false') } }] },
  visualContainerObjects: noChrome() });

const R = {
  title: [1, 1, 8, 3], slicer: [8, 1, 11, 2], legend: [8, 2, 11, 3], illus: [11, 1, 13, 3],
  kpis: [1, 3, 13, 5], answers: [1, 5, 13, 7],
  l1_band: [1, 7, 13, 9], l1_map: [1, 9, 6, 17], l1_heatmap: [6, 9, 10, 17], l1_ranking: [10, 9, 13, 17], l1_note: [1, 17, 13, 18],
  l2_band: [1, 18, 13, 20], l2_take: [1, 20, 7, 24], l2_receita: [7, 20, 13, 24], l2_repasse: [1, 24, 7, 27], l2_receita_min: [7, 24, 10, 27], l2_qualidade: [10, 24, 13, 27],
  l3_band: [1, 27, 13, 29], l3_map: [1, 29, 6, 38], l3_trend: [6, 29, 13, 33], l3_origem: [6, 33, 13, 38],
  l4_band: [1, 38, 13, 40], l4_map: [1, 40, 7, 49], l4_trend: [7, 40, 13, 44], l4_table: [7, 44, 13, 49],
  l5_band: [1, 49, 13, 51],
};
// revisão 5: raia 5 em px finais (a abertura termina em y = 4960); o add() sobe LANE_SHIFT, então ele é somado aqui
const at5 = (x, y, width, height) => ({ x, y: y + LANE_SHIFT, width, height });
const R5 = {
  exec: at5(48, 4976, 320, 56), exec_txt: at5(392, 4976, 1000, 56),
  cards: at5(48, 5048, 1344, 150),
  wape: at5(48, 5222, 544, 376), diario: at5(616, 5222, 776, 376),
  limites: at5(48, 5622, 1344, 120), // termina em 5742; rodapé em 5784
};
const LANE_ROWS = { 1: [7, 18], 2: [18, 27], 3: [27, 38], 4: [38, 49], 5: [49, 59] }; // [faixa início, raia fim) em linhas

// campos
const D = 'fct_demanda_zona_hora', H = 'fct_espera_histograma', O = 'fct_od_mensal';
const F = {
  corridas: mea(D, 'Corridas'), take: mea(D, 'Take rate'), rmilha: mea(D, 'Receita por milha'), rmin: mea(D, 'Receita por minuto'),
  repasse: mea(D, 'Repasse por hora de corrida'), invalida: mea(D, '% tarifa invalida'), share: mea(D, 'Share da operadora'),
  pctcbd: mea(D, '% destino no CBD'), p90: mea(H, 'Espera P90 (min)'), nesp: mea(H, 'Corridas com espera valida'),
  entrando: mea(O, 'Corridas entrando no CBD'), htmlkpi: mea(D, 'HTML Cartoes KPI'),
  zonaId: col('dim_zona', 'zona_id'), zona: col('dim_zona', 'zona'), borough: col('dim_zona', 'borough'),
  opId: col('dim_operadora', 'operadora_id'), op: col('dim_operadora', 'operadora'),
  mes: col('dim_mes', 'mes_inicio'), ano: col('dim_mes', 'ano'),
  hora: col('dim_periodo_espera', 'hora_do_dia'), tipo: col('dim_periodo_espera', 'tipo_dia'),
};
// revisão 5: campos da raia 5 (medidas ✍️ do Ronald; as de texto e HTML são de apresentação)
const P = 'ml_forecast_demanda', B = 'ml_backtest_metricas';
const F5 = {
  execucao: col('dim_execucao', 'execucao'), anoMes: col('dim_mes', 'ano_mes'), dia: col('dim_tempo_hora', 'data'),
  previsao: mea(P, 'Previsão Total'), realizado: mea(P, 'Realizado'),
  wapeModelo: mea(B, 'WAPE Modelo'), wapeBase: mea(B, 'WAPE Baseline'),
};
const ativas = () => fIn(F.opId, ['HV0003', 'HV0005']);
const soLyft = () => fIn(F.opId, ['HV0005']);
const opColors = () => ['Lyft', 'Uber'].map(o => ({ properties: { fill: fill(o === 'Lyft' ? C.lyft : C.uber) },
  selector: { data: [{ scopeId: { Comparison: { ComparisonKind: 0, Left: col('dim_operadora', 'operadora'), Right: { Literal: { Value: `'${o}'` } } } } }] } }));
function line(cat, y, series, color) {
  const qs = { Category: { projections: [proj(cat)] }, Y: { projections: [proj(y)] } };
  if (series) qs.Series = { projections: [proj(series)] };
  const v = { visualType: 'lineChart', query: { queryState: qs }, objects: {} };
  if (!series) v.objects.dataPoint = [{ properties: { defaultColor: fill(color) } }];
  else if (series.Column.Property === 'operadora') v.objects.dataPoint = opColors();
  else if (series.Column.Property === 'borough') // 3d: destaque em Manhattan (a história da raia 3); os demais em cinza
    v.objects.dataPoint = [['Manhattan', C.cbd], ['Brooklyn', '#6B7785'], ['Queens', '#9AA5B1'], ['Bronx', '#C3CBD4']].map(([b, cor]) => ({ properties: { fill: fill(cor) },
      selector: { data: [{ scopeId: { Comparison: { ComparisonKind: 0, Left: col('dim_zona', 'borough'), Right: { Literal: { Value: `'${b}'` } } } } }] } }));
  return v;
}
function shapeMap(value, loColor, hiColor, lo = null, hi = null) {
  // formato que o Desktop grava (paradas com expr); o formato sem expr deixou o mapa em branco (revisão 2)
  return { visualType: 'shapeMap',
    // revisão 4b: o visual não tem rótulos; o nome da zona aparece na dica de ferramenta (medida de apresentação)
    query: { queryState: { Category: { projections: [proj(F.zonaId, 'Código da zona')] }, Value: { projections: [proj(value)] },
      Tooltips: { projections: [proj(mea(D, 'Nome da zona'), 'Zona')] } } },
    objects: {
      shape: [{ properties: { datasourceType: str('file_upload'), projectionEnum: str('albersUsa'),
        map: { geoJson: { type: str('packaged'), name: str('zonas_tlc.json'),
          content: { expr: { ResourcePackageItem: { PackageName: 'RegisteredResources', PackageType: 1, ItemName: MAPA } } } } } } }],
      // 3d: limites fixos no mesmo formato nativo (com expr); se o mapa sumir, voltar sem lo/hi
      dataPoint: [{ properties: { fillRule: { linearGradient2: Object.assign(
        { min: Object.assign({ color: str(loColor) }, lo !== null ? { value: lit(lo) } : {}),
          max: Object.assign({ color: str(hiColor) }, hi !== null ? { value: lit(hi) } : {}) },
        { nullColoringStrategy: { strategy: str('noColor') } }) } } }],
    } };
}

// ===== cabeçalho (faixa azul-marinho de borda a borda) =====
add('hero_band', 'deco', { x: 0, y: 0, width: W, height: snap(M + 2 * ROW - G / 2) }, shape(C.navy));
// revisão 4: título e ficha em HTML com período e volume dinâmicos (medidas de apresentação)
const htmlVis = (measure, alt, extraVCO = {}, table = D) => ({ visualType: HTMLVIS,
  query: { queryState: { content: { projections: [proj(mea(table, measure))] } } },
  objects: { compatibility: [{ properties: { legacyRendering: lit('true') } }] },
  visualContainerObjects: Object.assign(noChrome(), { visualTooltip: [{ properties: { show: lit('false') } }],
    general: [{ properties: { altText: str(alt) } }] }, extraVCO) });
add('page_title', 0, { x: 48, y: 48, width: 776, height: 104 }, htmlVis('HTML Titulo', 'Título: cinco respostas para o time de Marketplace da Lyft, com o período dos dados.'));
add('header_ficha', 0, { x: 1104, y: 48, width: 288, height: 176 }, htmlVis('HTML Ficha Dados', 'Ficha dos dados: meses, zonas, viagens e último mês disponível.'));
// posições do cabeçalho ajustadas pelo Ronald no Desktop (commit 96ff690); legenda com 160 px para não sobrepor o filtro
add('month_slicer', 'slicer', { x: 220, y: 160, width: 320, height: 80 }, {
  visualType: 'slicer', query: { queryState: { Values: { projections: [proj(F.mes)] } } },
  objects: {
    data: [{ properties: { mode: str('Between') } }],
    header: [{ properties: { show: lit('true'), text: str('Período analisado'), fontFamily: str(FONT), textSize: lit('10D'), bold: lit('true'), fontColor: fill(C.navyTxt) } }],
    date: [{ properties: { fontFamily: str(FONT), textSize: lit('10D'), fontColor: fill(C.texto), background: fill('#FFFFFF') } }], // 3c: legível sobre o azul-marinho
    slider: [{ properties: { show: lit('true'), color: fill('#FFFFFF') } }],
  },
  visualContainerObjects: { background: [{ properties: { show: lit('false') } }], border: [{ properties: { show: lit('false') } }],
    padding: [{ properties: { top: lit('4D'), bottom: lit('4D'), left: lit('0D'), right: lit('0D') } }],
    visualHeader: [{ properties: { show: lit('false') } }],
    general: [{ properties: { altText: str('Filtro de período analisado (mês inicial e final); filtra todos os visuais da página.') } }] } },
  [fCmp(F.corridas, 1, '0L')]); // revisão 4: só meses com corridas (o calendário vai até dez/2026)
add('legend_ops', 0, { x: 48, y: 160, width: 160, height: 80 }, textbox([
  { textRuns: [run('OPERADORAS', 10, C.navyTxt, true)] },
  { textRuns: [run('● ', 14, C.lyft), run('Lyft   ', 13, '#FFFFFF', true), run('● ', 14, '#9AA5B1'), run('Uber', 13, '#FFFFFF', true)] },
  { textRuns: [run('Cores fixas em todos os gráficos', 11, C.navyTxt)] }]));
add('header_illus', 'deco', { x: 843.3333333333333, y: 13.333333333333332, width: 236.66666666666666, height: 212.22222222222223 }, { visualType: 'image',
  objects: { general: [{ properties: { imageUrl: { expr: { ResourcePackageItem: { PackageName: 'RegisteredResources', PackageType: 1, ItemName: ILUSTRACAO } } } } }],
    imageScaling: [{ properties: { imageScalingType: str('Fit') } }] },
  visualContainerObjects: Object.assign(noChrome(), { general: [{ properties: { altText: str('Ilustração: as 263 zonas de táxi de Nova York, com as 38 zonas do CBD em verde.') } }] }) });

// ===== abertura: cartões KPI em HTML (explicação ao passar o mouse) =====
add('kpi_html', 0, { x: 48, y: 272, width: 1344, height: 150 }, { visualType: HTMLVIS,
  query: { queryState: { content: { projections: [proj(F.htmlkpi)] } } },
  objects: { compatibility: [{ properties: { legacyRendering: lit('true') } }] },
  visualContainerObjects: Object.assign(noChrome(), { visualTooltip: [{ properties: { show: lit('false') } }],
    general: [{ properties: { altText: str('Seis indicadores do período: corridas, espera P90, take rate, receita por milha, % destino no CBD e share da Lyft. Passe o mouse para ver a definição.') } }] }) });
// revisão 6 (ADR 0023): as respostas e as aberturas das raias saem de medidas (HTML Resposta n / HTML Abertura n),
// com períodos por regra; o gerador não escreve mais nenhum número nem mês. Aqui fica só onde mora cada medida.
const TABELA_RAIA = { 1: H, 2: D, 3: D, 4: D, 5: P };
const lanes = Object.keys(TABELA_RAIA).map(Number);
const cartaoResposta = Object.assign(noChrome(), {
  background: [{ properties: { show: lit('true'), color: fill('#FFFFFF'), transparency: lit('0D') } }],
  border: [{ properties: { show: lit('true'), color: fill(C.borda), radius: lit('8D') } }],
  padding: [{ properties: { top: lit('12D'), bottom: lit('12D'), left: lit('14D'), right: lit('14D') } }] });
// revisão 6: cinco cartões (~250 px cada) com a altura toda da faixa (176 px) e respiro de 12 px; o texto das
// medidas vai em 13 px (os textos gerados são mais longos que os fixos da revisão 5 e cortavam em 160 px)
lanes.forEach((n, i) => add(`answer_${n}`, 0, box(R.answers, i + 1, lanes.length),
  htmlVis(`HTML Resposta ${n}`, `Resposta ${n}, gerada pelos dados: o resumo da raia ${n} e o período comparado.`, cartaoResposta, TABELA_RAIA[n])));

// ===== raias: linha fina na cor da raia + número + abertura (pergunta e resposta) =====
for (const n of lanes) {
  const [r0, r1] = LANE_ROWS[n];
  // revisão 4: sem preenchimento ("carnaval de cores"); linha fina na cor da raia + número e pergunta no tom escuro
  const top = snap(M + (r0 - 1) * ROW - G / 2);
  add(`l${n}_line`, 'deco', { x: 0, y: top, width: W, height: 4 }, shape(LANE[n]));
  add(`l${n}_num`, n, { x: M, y: top + 20, width: 104, height: 96 }, textbox([{ textRuns: [run(`0${n}`, 56, LANE[n], true)] }]));
  add(`l${n}_head`, n, { x: M + 128, y: top + 24, width: W - 2 * M - 128, height: 96 },
    htmlVis(`HTML Abertura ${n}`, `Pergunta e resposta da raia ${n}, geradas pelos dados.`, {}, TABELA_RAIA[n]));
}

// ===== raia 1: oferta =====
add('l1_map_p90', 1, alto(R.l1_map), { ...shapeMap(F.p90, C.p90t, C.p90, '6D', '15D'),
  visualContainerObjects: cardVCO('Espera P90 por zona de embarque (min)', mea(H, 'Subtitulo Mapa P90'), 'Mapa das zonas de NY coloridas pelo P90 da espera; mais escuro = espera maior. Zonas com menos de 100 corridas ficam sem cor.') },
  [fCmp(F.nesp, 2, '100L')]);
add('l1_heatmap_hora', 1, alto(R.l1_heatmap), { visualType: 'pivotTable',
  query: { queryState: { Rows: { projections: [proj(F.hora, 'Hora do dia')] }, Columns: { projections: [proj(F.tipo, 'Tipo de dia')] }, Values: { projections: [proj(F.p90, 'P90 (min)')] } } },
  objects: {
    columnHeaders: [{ properties: { columnAdjustment: str('growToFit'), autoSizeColumnWidth: lit('true') } }],
    values: [{ properties: { backColor: { solid: { color: { expr: { FillRule: { Input: { SelectRef: { ExpressionName: qref(F.p90) } },
      FillRule: { linearGradient2: { min: { color: { Literal: { Value: "'#FFFFFF'" } } }, max: { color: { Literal: { Value: `'${C.p90}'` } } },
        nullColoringStrategy: { strategy: { Literal: { Value: "'noColor'" } } } } } } } } } } },
      selector: { data: [{ dataViewWildcard: { matchingOption: 1 } }], metadata: qref(F.p90) } }] },
  visualContainerObjects: cardVCO('P90 por hora do dia e tipo de dia (min)', mea(H, 'Subtitulo Heatmap P90'), 'Matriz de calor: P90 da espera por hora do dia (linhas) e tipo de dia (colunas); célula mais escura = espera maior.') });
add('l1_ranking_zonas', 1, alto(R.l1_ranking), { visualType: 'clusteredBarChart',
  query: { queryState: { Category: { projections: [proj(F.zona)] }, Y: { projections: [proj(F.p90)] } },
    sortDefinition: { sort: [{ field: F.p90, direction: 'Descending' }], isDefaultSort: false } },
  objects: { dataPoint: [{ properties: { defaultColor: fill(C.p90) } }], labels: [{ properties: { show: lit('true') } }] },
  visualContainerObjects: cardVCO('Zonas com P90 de 12 min ou mais', mea(H, 'Subtitulo Ranking P90'), 'Barras: zonas com 1.000 ou mais corridas e P90 de 12 minutos ou mais, da maior para a menor espera.') },
  [fCmp(F.nesp, 2, '1000L'), fCmp(F.p90, 2, '12D'), fCmp(F.zonaId, 4, '263L')]);
add('l1_note', 1, R.l1_note, textbox([{ textRuns: [run('Como ler: P90 é o tempo até o qual 9 em cada 10 corridas esperaram, do pedido ao embarque. Acima de 15 min, o valor é estimado, com margem de até 1 minuto. Zonas com menos de 100 corridas no período escolhido ficam sem cor.', 11, C.sub)] }]));

// ===== raia 2: economia =====
add('l2_take_trend', 2, R.l2_take, { ...line(F.mes, F.take, F.op),
  visualContainerObjects: cardVCO('Take rate por operadora (mês)', mea(D, 'Subtitulo Take Rate Operadoras'), 'Linhas: take rate mensal da Uber (cinza) e da Lyft (rosa-púrpura).') }, [ativas()]);
add('l2_receita_trend', 2, R.l2_receita, { ...line(F.mes, F.rmilha, null, C.eco),
  visualContainerObjects: cardVCO('Receita por milha (US$, mês)', mea(D, 'Subtitulo Receita Milha'), 'Linha: receita por milha mensal, em dólares.') });
add('l2_repasse_trend', 2, R.l2_repasse, { ...line(F.mes, F.repasse, null, C.repasse),
  visualContainerObjects: cardVCO('Repasse por hora de corrida (US$, mês)', mea(D, 'Subtitulo Repasse Hora'), 'Linha: repasse ao motorista por hora de corrida, mensal. Não é o ganho por hora do motorista (sem tempo ocioso no dado).') });
add('l2_receita_min_ano', 2, R.l2_receita_min, { visualType: 'clusteredColumnChart',
  query: { queryState: { Category: { projections: [proj(F.ano)] }, Y: { projections: [proj(F.rmin)] } },
    sortDefinition: { sort: [{ field: F.ano, direction: 'Ascending' }], isDefaultSort: false } },
  objects: { dataPoint: [{ properties: { defaultColor: fill(C.eco) } }], labels: [{ properties: { show: lit('true') } }] },
  visualContainerObjects: cardVCO('Receita por minuto (US$, ano)', mea(D, 'Subtitulo Receita Minuto'), 'Colunas: receita por minuto de corrida em cada ano do período escolhido.') });
add('l2_qualidade_card', 2, R.l2_qualidade, { visualType: 'cardVisual',
  query: { queryState: { Data: { projections: [proj(F.invalida, '% tarifa ≤ 0')] } } },
  objects: { accentBar: [{ properties: { show: lit('true'), color: fill(C.uber) }, selector: { id: 'default' } }] },
  visualContainerObjects: cardVCO('Qualidade do dado', 'Fica fora das métricas de economia', 'Parcela das corridas com tarifa menor ou igual a zero, excluídas das métricas de economia.') });

// ===== raia 3: CBD =====
add('l3_map_origem', 3, R.l3_map, { ...shapeMap(F.entrando, C.cbdt, C.cbd),
  visualContainerObjects: cardVCO('Origem das corridas que entram no CBD', mea(O, 'Subtitulo Origem CBD Mapa'), 'Mapa: zonas de embarque coloridas pelo número de corridas que terminam no CBD vindas de fora dele.') });
add('l3_pct_trend', 3, R.l3_trend, { ...line(F.mes, F.pctcbd, null, C.cbd),
  visualContainerObjects: cardVCO('% das corridas com destino no CBD (mês)', mea(D, 'Subtitulo Fatia CBD'), 'Linha: porcentagem mensal das corridas com destino no CBD; a taxa de congestionamento começou em 05/01/2025.') });
add('l3_origem_trend', 3, R.l3_origem, { ...line(F.mes, F.entrando, F.borough, null),
  visualContainerObjects: cardVCO('Corridas que entram no CBD, por distrito de origem (mês)', mea(O, 'Subtitulo Origem CBD Distritos'), 'Linhas: corridas mensais que entram no CBD vindas de Manhattan, Brooklyn, Queens e Bronx.') },
  [fIn(F.borough, ['Manhattan', 'Brooklyn', 'Queens', 'Bronx'])]);

// ===== raia 4: Uber x Lyft =====
add('l4_map_share', 4, R.l4_map, { ...shapeMap(F.share, C.lyftt, C.lyft, '0.15D', '0.4D'),
  visualContainerObjects: cardVCO('Share da Lyft por zona de embarque', mea(D, 'Subtitulo Mapa Share'), 'Mapa: share da Lyft em cada zona; mais escuro = share maior.') }, [soLyft()]);
add('l4_share_trend', 4, R.l4_trend, { ...line(F.mes, F.share, F.op),
  visualContainerObjects: cardVCO('Share por operadora (mês)', mea(D, 'Subtitulo Share Tendencia'), 'Linhas: share mensal da Uber (cinza) e da Lyft (rosa-púrpura).') }, [ativas()]);
add('l4_table_zonas', 4, R.l4_table, { visualType: 'tableEx',
  query: { queryState: { Values: { projections: [proj(F.zona, 'Zona'), proj(F.borough, 'Distrito'), proj(F.corridas, 'Corridas da Lyft'), proj(F.share, 'Share da Lyft')] } },
    sortDefinition: { sort: [{ field: F.corridas, direction: 'Descending' }], isDefaultSort: false } },
  objects: {
    columnHeaders: [{ properties: { columnAdjustment: str('growToFit'), autoSizeColumnWidth: lit('true') } }],
    // revisão 4: barras de dados nas corridas; gradiente de uma cor no share (escala fixa 20%–35%, coerente com o mapa)
    columnFormatting: [{ properties: { dataBars: {
      positiveColor: fill(C.lyftt), negativeColor: fill('#D64554'), axisColor: fill('#999999'),
      reverseDirection: lit('false'), hideText: lit('false') } }, selector: { metadata: qref(F.corridas) } }],
    values: [{ properties: { backColor: { solid: { color: { expr: { FillRule: { Input: { SelectRef: { ExpressionName: qref(F.share) } },
      FillRule: { linearGradient2: { min: { color: { Literal: { Value: "'#FFFFFF'" } }, value: { Literal: { Value: '0.2D' } } },
        max: { color: { Literal: { Value: `'${C.lyft}'` } }, value: { Literal: { Value: '0.35D' } } },
        nullColoringStrategy: { strategy: { Literal: { Value: "'noColor'" } } } } } } } } } } },
      selector: { data: [{ dataViewWildcard: { matchingOption: 1 } }], metadata: qref(F.share) } }],
  },
  visualContainerObjects: cardVCO('20 zonas com mais corridas da Lyft', mea(D, 'Subtitulo Tabela Lyft'), 'Tabela: as 20 zonas com mais corridas da Lyft, com distrito, corridas e share da Lyft.') },
  [soLyft(), fTopN(F.zona, 20, D, 'qtd_corridas')]);

// ===== raia 5: previsto × realizado (Fase 5) =====
// segmentação de execução: seleção única, SEM pré-seleção (revisão 6, ADR 0023). Sem seleção, as medidas usam a
// execução padrão por regra ([Execucao Alvo] e dim_execucao[is_padrao]); nunca somam execuções. Lista suspensa
// para caber numa linha da grade.
add('l5_exec_slicer', 5, R5.exec, {
  visualType: 'slicer', query: { queryState: { Values: { projections: [proj(F5.execucao, 'Execução do modelo')] } } },
  objects: {
    data: [{ properties: { mode: str('Dropdown') } }],
    selection: [{ properties: { singleSelect: lit('true') } }],
    header: [{ properties: { show: lit('true'), text: str('Execução do modelo'), fontFamily: str(FONT), textSize: lit('10D'), bold: lit('true'), fontColor: fill(LANE[5]) } }],
    items: [{ properties: { fontFamily: str(FONT), textSize: lit('10D'), fontColor: fill(C.texto) } }],
  },
  visualContainerObjects: { background: [{ properties: { show: lit('false') } }], border: [{ properties: { show: lit('false') } }],
    padding: [{ properties: { top: lit('0D'), bottom: lit('0D'), left: lit('0D'), right: lit('0D') } }],
    visualHeader: [{ properties: { show: lit('false') } }],
    general: [{ properties: { altText: str('Escolha da execução do modelo (uma por vez); filtra só a raia 5.') } }] } });
add('l5_exec_txt', 5, R5.exec_txt, htmlVis('HTML Execucao no Ar', 'Qual execução do modelo está no ar, ou um aviso se nenhuma estiver selecionada.', {}, P));

// revisão 5b (pedido do Ronald): cartões em HTML, no padrão da abertura; o valor cabe inteiro e a métrica é
// explicada ao passar o mouse
add('l5_cards_html', 5, R5.cards, htmlVis('HTML Cartoes Previsao', 'Cinco indicadores da previsão: erro do modelo, erro do palpite sazonal, vantagem, janelas vencidas e previsão do mês seguinte. Passe o mouse para ver a definição.', {}, P));

add('l5_wape_mes', 5, R5.wape, { visualType: 'clusteredColumnChart',
  query: { queryState: { Category: { projections: [proj(F5.anoMes, 'Mês')] },
    Y: { projections: [proj(F5.wapeModelo, 'Modelo'), proj(F5.wapeBase, 'Palpite sazonal')] } },
    sortDefinition: { sort: [{ field: F5.anoMes, direction: 'Ascending' }], isDefaultSort: false } },
  objects: { dataPoint: [{ properties: { fill: fill(LANE[5]) }, selector: { metadata: qref(F5.wapeModelo) } },
    { properties: { fill: fill(BASELINE) }, selector: { metadata: qref(F5.wapeBase) } }],
    labels: [{ properties: { show: lit('true') } }] },
  visualContainerObjects: cardVCO('Erro por janela testada: modelo × palpite sazonal', mea(B, 'Subtitulo WAPE Janelas'),
    'Colunas: erro percentual (WAPE) do modelo (índigo) e do palpite sazonal (cinza) em cada mês testado da execução escolhida.') });
add('l5_diario', 5, R5.diario, { visualType: 'lineChart',
  query: { queryState: { Category: { projections: [proj(F5.dia, 'Dia')] },
    Y: { projections: [proj(F5.previsao, 'Previsto'), proj(F5.realizado, 'Realizado')] } } },
  objects: { dataPoint: [{ properties: { fill: fill(LANE[5]) }, selector: { metadata: qref(F5.previsao) } },
    { properties: { fill: fill(C.uber) }, selector: { metadata: qref(F5.realizado) } }] },
  visualContainerObjects: cardVCO('Corridas por dia: previsto × realizado', mea(P, 'Subtitulo Previsto Realizado'),
    'Linhas: corridas diárias previstas pelo modelo (índigo) e realizadas (cinza escuro) nos meses da execução escolhida; o último mês só tem a previsão.') });
add('l5_limites', 5, R5.limites, htmlVis('HTML Limitacoes', 'As três limitações da previsão: viés para baixo, clima observado e atraso dos dados da TLC.', {}, P));

// ===== rodapé (faixa azul-marinho) com fonte e links =====
const fy = FOOTER_Y;
add('footer_band', 'deco', { x: 0, y: fy, width: W, height: PAGE_H - fy }, shape(C.navy));
add('footer_text', 0, { x: M, y: fy + 20, width: 900, height: 80 }, htmlVis('HTML Rodape', 'Fonte dos dados e nota sobre o projeto.')); // revisão 4: texto para o usuário final
const links = [['Portfólio', LINKS.portfolio], ['GitHub', LINKS.github], ['LinkedIn', LINKS.linkedin]].filter(([, u]) => u);
links.forEach(([label, url], i) => add(`link_${label}`, 'deco', { x: W - M - (links.length - i) * 128, y: fy + 32, width: 112, height: 40 }, textbox(
  [{ textRuns: [run(`${label} ↗`, 13, '#FFFFFF', true)], horizontalTextAlignment: 'center' }],
  Object.assign(noChrome(), {
    border: [{ properties: { show: lit('true'), color: fill(C.navyTxt), radius: lit('20D') } }],
    padding: [{ properties: { top: lit('8D'), bottom: lit('8D'), left: lit('8D'), right: lit('8D') } }],
    visualLink: [{ properties: { show: lit('true'), type: str('WebUrl'), webUrl: str(url) } }],
    general: [{ properties: { altText: str(`Abrir ${label} de Ronald Martins`) } }] }))));

// ---------- interações: clique só filtra a própria raia ----------
const dataVisuals = visuals.filter(v => v.json.visual.query && v.lane !== 'slicer');
const byId = id => visuals.find(v => v.id === id);
const execucao = byId('l5_exec_slicer');
// revisão 6: a escolha da execução também alimenta a resposta 5 do cabeçalho (é a mesma pergunta)
const segue = (s, t) => s === execucao && t.id === 'answer_5';
// revisão 6: respostas e aberturas são "a resposta" (ADR 0023, princípio 3): não seguem cliques; a abertura 5 segue
// só a execução escolhida
const ehResposta = v => /^answer_\d$/.test(v.id) || /^l\d_head$/.test(v.id);
const interactions = [];
for (const s of dataVisuals) for (const t of dataVisuals) {
  if (s === t || segue(s, t)) continue;
  if (s.lane !== t.lane || (ehResposta(t) && s !== execucao)) interactions.push({ source: s.name, target: t.name, type: 'NoFilter' });
}
// revisão 5 (decisão 1): o filtro de período não alcança a raia 5 (ela mostra sempre as janelas testadas e o mês
// previsto); revisão 6: nem as respostas e aberturas, que usam os períodos por regra
const periodo = byId('month_slicer');
for (const t of dataVisuals) if (t.lane === 5 || ehResposta(t)) interactions.push({ source: periodo.name, target: t.name, type: 'NoFilter' });

// ---------- escrita: visuais e página ----------
fs.rmSync(visualsDir, { recursive: true, force: true });
fs.mkdirSync(visualsDir, { recursive: true });
for (const v of visuals) {
  fs.mkdirSync(path.join(visualsDir, v.name), { recursive: true });
  fs.writeFileSync(path.join(visualsDir, v.name, 'visual.json'), JSON.stringify(v.json, null, 2) + '\n');
}
const pageFile = path.join(pageDir, 'page.json');
const page = JSON.parse(fs.readFileSync(pageFile, 'utf8'));
Object.assign(page, { displayName: 'Rideshare em NY — cinco respostas', displayOption: DISPLAY, width: W, height: PAGE_H,
  objects: { background: [{ properties: { color: fill(C.fundo), transparency: lit('0D') } }] }, visualInteractions: interactions });
fs.writeFileSync(pageFile, JSON.stringify(page, null, 2) + '\n');

// ---------- tema (fonte única + paleta) e registro no report.json ----------
const tema = {
  name: TEMA, // igual ao registro, com .json (theming.md; PBIR_THEME_FILE_NAME_MISMATCH)
  dataColors: ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#56B4E9', '#E69F00', '#4D4D4D', '#F0E442'],
  foreground: C.texto, background: '#FFFFFF', tableAccent: C.eco,
  textClasses: {
    callout: { fontFace: FONT, fontSize: 28, color: C.texto },
    title: { fontFace: FONT, fontSize: 12, color: C.texto },
    header: { fontFace: FONT, fontSize: 12, color: C.texto },
    label: { fontFace: FONT, fontSize: 10, color: C.texto },
    largeTitle: { fontFace: FONT, fontSize: 14, color: C.texto },
    semiboldLabel: { fontFace: FONT, fontSize: 10, color: C.texto, bold: true },
    boldLabel: { fontFace: FONT, fontSize: 10, color: C.texto, bold: true },
  },
};
for (const f of fs.readdirSync(rrDir)) if (/^RideshareTema-.*\.json$/.test(f) && f !== TEMA) fs.rmSync(path.join(rrDir, f));
fs.writeFileSync(path.join(rrDir, TEMA), JSON.stringify(tema, null, 2) + '\n');
const repFile = path.join(reportDir, 'definition', 'report.json');
const rep = JSON.parse(fs.readFileSync(repFile, 'utf8'));
rep.themeCollection.customTheme = { name: TEMA, reportVersionAtImport: rep.themeCollection.baseTheme.reportVersionAtImport, type: 'RegisteredResources' };
let pkg = rep.resourcePackages.find(p => p.name === 'RegisteredResources');
if (!pkg) { pkg = { name: 'RegisteredResources', type: 'RegisteredResources', items: [] }; rep.resourcePackages.push(pkg); }
pkg.items = pkg.items.filter(i => !/^RideshareTema-/.test(i.name) && i.name !== ILUSTRACAO);
pkg.items.push({ name: TEMA, path: TEMA, type: 'CustomTheme' }, { name: ILUSTRACAO, path: ILUSTRACAO, type: 'Image' });
rep.publicCustomVisuals = Array.from(new Set([...(rep.publicCustomVisuals || []), HTMLVIS]));
fs.writeFileSync(repFile, JSON.stringify(rep, null, 2) + '\n');

console.log(JSON.stringify({ visuais: visuals.length, dados: dataVisuals.length, interacoes: interactions.length, links: links.map(l => l[0]),
  maiorY: Math.max(...visuals.map(v => v.json.position.y + v.json.position.height)) }));
