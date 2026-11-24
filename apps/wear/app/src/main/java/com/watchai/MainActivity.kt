package com.watchai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.watchai.application.WatchAiApp
import com.watchai.application.WatchController

class MainActivity : ComponentActivity() {
    private lateinit var controller: WatchController

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        controller = WatchController(applicationContext)
        setContent { WatchAiApp(controller) }
        controller.start()
    }

    override fun onStart() {
        super.onStart()
        if (::controller.isInitialized) controller.setForegroundActive(true)
    }

    override fun onStop() {
        if (::controller.isInitialized) controller.setForegroundActive(false)
        super.onStop()
    }

    override fun onDestroy() {
        if (::controller.isInitialized && isFinishing) controller.close()
        super.onDestroy()
    }
}
