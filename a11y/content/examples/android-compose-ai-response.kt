import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics

@Composable
fun AccessibleAiTurn(
    userText: String,
    finalAnswer: String?,
    isGenerating: Boolean,
    onSend: () -> Unit,
) {
    Column {
        Text("Você")
        Text(userText)

        // One visible state. Do not add a liveRegion to streamed tokens or tool progress.
        if (isGenerating) Text("Digitando...")

        if (finalAnswer != null) {
            Text("IA Assistente")
            Text(finalAnswer)
        }

        Button(onClick = onSend, enabled = !isGenerating) {
            Text("Enviar mensagem")
        }
    }
}

// For a product that explicitly requires automatic completion speech, emit one
// bounded platform announcement from the event layer after success. Never keep
// a second hidden copy of finalAnswer in the Compose semantics tree.
