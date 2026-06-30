package br.com.corepet.app

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.Intent
import android.net.Uri
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class FuncionarioFileShareModule(
  private val reactContext: ReactApplicationContext,
) : ReactContextBaseJavaModule(reactContext) {
  override fun getName(): String = "FuncionarioFileShare"

  @ReactMethod
  fun shareFile(uri: String, mimeType: String?, title: String?, promise: Promise) {
    try {
      val arquivoUri = Uri.parse(uri)
      val tipo = mimeType?.takeIf { it.isNotBlank() } ?: "application/octet-stream"
      val nome = title?.takeIf { it.isNotBlank() } ?: "arquivo"
      val sendIntent = Intent(Intent.ACTION_SEND).apply {
        type = tipo
        putExtra(Intent.EXTRA_STREAM, arquivoUri)
        putExtra(Intent.EXTRA_SUBJECT, nome)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        clipData = ClipData.newUri(reactContext.contentResolver, nome, arquivoUri)
      }
      val chooser = Intent.createChooser(sendIntent, nome).apply {
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
      }
      val activity = reactContext.currentActivity
      if (activity != null) {
        activity.startActivity(chooser)
      } else {
        chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        reactContext.startActivity(chooser)
      }
      promise.resolve(true)
    } catch (error: ActivityNotFoundException) {
      promise.reject("E_SHARE_UNAVAILABLE", "Nenhum app disponivel para compartilhar.", error)
    } catch (error: Exception) {
      promise.reject("E_SHARE_FILE", "Nao foi possivel compartilhar o arquivo.", error)
    }
  }
}
