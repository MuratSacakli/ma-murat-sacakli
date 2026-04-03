package com.example.mymasterarbeit

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.example.mymasterarbeit.databinding.ActivityMainBinding
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var clickCount = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.greetButton.setOnClickListener {
            clickCount++
            val name = binding.nameInput.text.toString().trim()
            val greeting = if (name.isNotEmpty()) {
                getString(R.string.greeting_with_name, name)
            } else {
                getString(R.string.greeting_default)
            }
            binding.greetingText.text = greeting
            binding.greetingText.visibility = View.VISIBLE
            binding.clickCountText.text = getString(R.string.click_count, clickCount)
        }

        binding.resetButton.setOnClickListener {
            clickCount = 0
            binding.nameInput.text?.clear()
            binding.greetingText.visibility = View.GONE
            binding.clickCountText.text = getString(R.string.click_count, clickCount)
        }

        val dateFormat = SimpleDateFormat("dd.MM.yyyy", Locale.GERMANY)
        binding.dateText.text = getString(R.string.current_date, dateFormat.format(Date()))
    }
}
