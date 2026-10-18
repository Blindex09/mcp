import SwiftUI

struct AccessibleAITurn: View {
    let userText: String
    let finalAnswer: String?
    let isGenerating: Bool
    let onSend: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Você").font(.headline)
            Text(userText)

            // Keep streamed tokens and tool progress silent by default.
            if isGenerating {
                Text("Digitando...")
            }

            if let finalAnswer {
                Text("IA Assistente").font(.headline)
                Text(finalAnswer)
            }

            Button("Enviar mensagem", action: onSend)
                .disabled(isGenerating)
        }
        .dynamicTypeSize(...DynamicTypeSize.accessibility5)
    }
}

// If product research requires automatic completion speech, post one bounded
// UIAccessibility announcement after success. Do not add a hidden duplicate of
// finalAnswer to the persistent VoiceOver accessibility hierarchy.
