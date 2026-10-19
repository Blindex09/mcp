"""Cenarios de Android (Jetpack Compose) e iOS (SwiftUI/UIKit): codigo e regra, NAO executados aqui.

Este MCP nao tem executor de Android nem de iOS: nao ha TalkBack nem VoiceOver para medir. Por isso estes exemplos mostram o codigo ruim e o bom
e a regra, e a pagina diz claramente que nada foi medido. As APIs do Android foram conferidas em developer.android.com (semantica do Compose, lida em
2026-10-19). As do iOS vieram de artigos de terceiros: a pagina oficial da Apple nao pode ser lida, confirme em developer.apple.com antes de copiar.
"""

from __future__ import annotations

from typing import Any

AVISO_ANDROID = "Não executado aqui: este MCP não tem Android. O código segue a documentação do Jetpack Compose (developer.android.com, semântica de acessibilidade, lida em 2026-10-19). Teste com o TalkBack num aparelho ou emulador."
AVISO_IOS = "Não executado aqui: este MCP não tem iOS. As APIs vieram de artigos de terceiros; a página oficial da Apple não pôde ser lida. Confirme em developer.apple.com e teste com o VoiceOver num aparelho."


def _ex(tipo: str, titulo: str, codigo: str, porque: str, corrigir: str, aviso: str) -> dict[str, Any]:
    return {"tipo": tipo, "titulo": titulo, "nao_executado": aviso, "codigo": codigo, "html": "", "porque": porque, "corrigir": corrigir}


MOBILE: list[dict[str, Any]] = [
    {
        "slug": "android",
        "nome": "Android (Jetpack Compose)",
        "resumo": "No Compose a acessibilidade vem da árvore de semântica. clickable, toggleable e ListItem já juntam os filhos num só item; ícones precisam de descrição; mudanças que o usuário não vê precisam de liveRegion; títulos de seção usam heading().",
        "exemplos": [
            _ex("ruim", "Ícone clicável sem descrição", """Icon(
    imageVector = Icons.Default.Favorite,
    contentDescription = null,
    modifier = Modifier.clickable { curtir() }
)""",
                "O TalkBack encontra um item clicável sem nome: diz só que é botão ou nada. Com contentDescription nulo, o ícone não tem texto nenhum. A área de toque também não é garantida.",
                "Use IconButton com contentDescription que diga a ação (\"Curtir\"). contentDescription = null só serve quando um texto ao lado já dá o nome.", AVISO_ANDROID),
            _ex("bom", "IconButton com descrição", """IconButton(onClick = { curtir() }) {
    Icon(
        imageVector = Icons.Default.Favorite,
        contentDescription = "Curtir"
    )
}""",
                "O IconButton traz o papel de botão e a área de toque mínima; a descrição diz a ação.",
                "Nada a corrigir.", AVISO_ANDROID),
            _ex("ruim", "Mensagem de status que muda em silêncio", """var status by remember { mutableStateOf("") }
Button(onClick = { status = "Salvo com sucesso" }) { Text("Salvar") }
Text(status)""",
                "O texto muda na tela, mas nenhum serviço de acessibilidade é avisado: quem usa o TalkBack não ouve que salvou.",
                "Marque o texto de status como região viva.", AVISO_ANDROID),
            _ex("bom", "Região viva educada", """var status by remember { mutableStateOf("") }
Button(onClick = { status = "Salvo com sucesso" }) { Text("Salvar") }
Text(
    text = status,
    modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite }
)""",
                "liveRegion = Polite faz o TalkBack anunciar a mudança sem interromper. Use Assertive só para o que não pode esperar, e nunca em texto que muda o tempo todo, como um cronômetro.",
                "Nada a corrigir.", AVISO_ANDROID),
            _ex("ruim", "Título de seção que é só texto grande", """Text("Pedidos recentes", style = MaterialTheme.typography.headlineSmall)""",
                "Para quem vê é um título. Para o TalkBack é uma linha de texto: não dá para pular de seção em seção.",
                "Marque como título na semântica.", AVISO_ANDROID),
            _ex("bom", "Título marcado com heading()", """Text(
    text = "Pedidos recentes",
    style = MaterialTheme.typography.headlineSmall,
    modifier = Modifier.semantics { heading() }
)""",
                "heading() deixa os serviços de acessibilidade navegarem direto entre os títulos.",
                "Nada a corrigir.", AVISO_ANDROID),
        ],
    },
    {
        "slug": "ios",
        "nome": "iOS (SwiftUI e UIKit)",
        "resumo": "No iOS o VoiceOver lê o rótulo, o valor e os traços de cada elemento. Toque num texto ou imagem com onTapGesture não vira botão; imagens decorativas precisam sair da árvore; mudanças que o usuário não vê precisam ser anunciadas.",
        "exemplos": [
            _ex("ruim", "Imagem com onTapGesture", """Image(systemName: "heart")
    .onTapGesture { curtir() }""",
                "O VoiceOver lê o nome do símbolo (\"heart\") ou nada, sem dizer que é botão, e o toque pode ficar menor que o mínimo.",
                "Use Button e dê um rótulo que diga a ação.", AVISO_IOS),
            _ex("bom", "Button com rótulo", """Button(action: curtir) {
    Image(systemName: "heart")
}
.accessibilityLabel("Curtir")""",
                "Button traz o traço de botão; accessibilityLabel diz a ação em vez do nome do símbolo.",
                "Nada a corrigir.", AVISO_IOS),
            _ex("ruim", "Título de seção que é só texto grande", """Text("Pedidos recentes")
    .font(.title2)""",
                "Para quem vê é um título. Para o VoiceOver é texto comum: o rotor de títulos não o encontra.",
                "Acrescente o traço de título.", AVISO_IOS),
            _ex("bom", "Título com o traço isHeader", """Text("Pedidos recentes")
    .font(.title2)
    .accessibilityAddTraits(.isHeader)""",
                "O traço isHeader põe o texto no rotor de títulos do VoiceOver.",
                "Nada a corrigir.", AVISO_IOS),
            _ex("ruim", "Mensagem de status que só aparece na tela", """@State private var status = ""
Button("Salvar") { status = "Salvo com sucesso" }
Text(status)""",
                "O texto muda, mas o VoiceOver não é avisado: quem não vê a tela não sabe que salvou.",
                "Poste um anúncio de acessibilidade quando o estado mudar.", AVISO_IOS),
            _ex("bom", "Anúncio de acessibilidade", """@State private var status = ""
Button("Salvar") {
    status = "Salvo com sucesso"
    UIAccessibility.post(notification: .announcement, argument: status)
}
Text(status)""",
                "UIAccessibility.post com a notificação de anúncio faz o VoiceOver falar a mensagem. No iOS 17 também existe a forma de SwiftUI (AccessibilityNotification); confirme na documentação da Apple.",
                "Nada a corrigir.", AVISO_IOS),
        ],
    },
]
