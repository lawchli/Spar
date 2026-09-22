package org.xz1.audio;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.*;
import android.media.audiofx.*;
import android.os.*;
import android.graphics.Color;
import android.util.Log;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.text.SimpleDateFormat;
import java.util.*;

/** No network permission, no routing overrides outside this AudioRecord. */
public class MainActivity extends Activity {
    private final Handler main = new Handler(Looper.getMainLooper());
    private AudioManager manager;
    private RadioGroup inputs;
    private Spinner sources;
    private EditText seconds;
    private CheckBox strict;
    private TextView preferred, actual, status, meter;
    private Button start, stop;
    private int selectedId = -1;
    private String selectedKey = null; // null means explicit system default
    private AudioDeviceInfo[] devices = new AudioDeviceInfo[0];
    private volatile boolean running;
    private Thread worker;
    private PrintWriter events;
    private boolean destroyed;
    private final String[] sourceNames = {"UNPROCESSED", "MIC", "DEFAULT", "CAMCORDER"};
    private final int[] sourceValues = {MediaRecorder.AudioSource.UNPROCESSED, MediaRecorder.AudioSource.MIC,
            MediaRecorder.AudioSource.DEFAULT, MediaRecorder.AudioSource.CAMCORDER};

    private final AudioDeviceCallback deviceCallback = new AudioDeviceCallback() {
        @Override public void onAudioDevicesAdded(AudioDeviceInfo[] d) { refresh(); }
        @Override public void onAudioDevicesRemoved(AudioDeviceInfo[] d) { refresh(); }
    };
    private final AudioManager.AudioRecordingCallback recordingCallback = new AudioManager.AudioRecordingCallback() {
        @Override public void onRecordingConfigChanged(List<AudioRecordingConfiguration> configs) {
            for (AudioRecordingConfiguration c : configs) {
                JSONObject j = new JSONObject();
                put(j, "session", c.getClientAudioSessionId());
                put(j, "client_source", c.getClientAudioSource());
                put(j, "device", describe(c.getAudioDevice()));
                put(j, "client_format", c.getClientFormat().toString());
                put(j, "device_format", c.getFormat().toString());
                if (Build.VERSION.SDK_INT >= 29) {
                    put(j, "silenced", c.isClientSilenced());
                    put(j, "client_effects", effectDescriptions(c.getClientEffects()));
                    put(j, "effects", effectDescriptions(c.getEffects()));
                }
                emit("recording_configuration", j);
            }
        }
    };

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        manager = (AudioManager)getSystemService(AUDIO_SERVICE);
        try {
            File dir = getExternalFilesDir(null);
            if (dir == null) dir = getFilesDir();
            events = new PrintWriter(new FileWriter(new File(dir, "events-" + System.currentTimeMillis() + ".jsonl"), true), true);
        } catch (IOException e) { Log.e("XZ1Audio", "Cannot open event file", e); }
        ScrollView scroll = new ScrollView(this);
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(24, 32, 24, 24);
        scroll.addView(column); setContentView(scroll);
        text(column, "XZ1 Audio Probe · mono PCM16 / 48 kHz", 22);
        text(column, "Inputs from AudioManager.GET_DEVICES_INPUTS. Empty capability arrays mean unspecified, not unsupported.", 13);
        String unprocessed = manager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED);
        text(column, "UNPROCESSED supported: " + unprocessed + "\nCheck JSONL + audio_flinger for vendor effects.", 14);
        emit("unprocessed_support", unprocessed);
        inputs = new RadioGroup(this); column.addView(inputs);
        sources = new Spinner(this);
        sources.setAdapter(new ArrayAdapter<String>(this, android.R.layout.simple_spinner_dropdown_item, sourceNames));
        column.addView(sources);
        seconds = new EditText(this); seconds.setInputType(2); seconds.setText("5"); seconds.setHint("Seconds (1–300)");
        column.addView(seconds);
        strict = new CheckBox(this); strict.setText("Stop if actual route differs (recommended)"); strict.setChecked(true);
        column.addView(strict);
        preferred = text(column, "Preferred input: System default", 16);
        actual = text(column, "Actual routed input: not recording", 16);
        meter = text(column, "RMS: —", 18);
        status = text(column, "Idle", 15);
        start = new Button(this); start.setText("Start"); column.addView(start);
        stop = new Button(this); stop.setText("Stop"); stop.setEnabled(false); column.addView(stop);
        start.setOnClickListener(v -> begin());
        stop.setOnClickListener(v -> { running = false; status.setText("Stopping…"); });
        manager.registerAudioDeviceCallback(deviceCallback, main);
        manager.registerAudioRecordingCallback(recordingCallback, main);
        refresh();
        handleIntent(getIntent());
    }

    private TextView text(LinearLayout p, String value, int size) {
        TextView t = new TextView(this); t.setText(value); t.setTextSize(size); t.setPadding(0, 8, 0, 8); p.addView(t); return t;
    }
    private static void put(JSONObject j, String key, Object value) {
        try { j.put(key, value == null ? JSONObject.NULL : value); } catch (JSONException ignored) {}
    }
    private synchronized void emit(String event, Object detail) {
        JSONObject j = new JSONObject();
        put(j, "wall_ms", System.currentTimeMillis()); put(j, "elapsed_ns", SystemClock.elapsedRealtimeNanos());
        put(j, "event", event); put(j, "detail", detail);
        Log.i("XZ1Audio", j.toString());
        if (events != null) events.println(j);
    }
    private static JSONArray effectDescriptions(List<AudioEffect.Descriptor> effects) {
        JSONArray result = new JSONArray();
        for (AudioEffect.Descriptor d : effects) {
            JSONObject j = new JSONObject();
            put(j, "name", d.name); put(j, "implementor", d.implementor);
            put(j, "uuid", d.uuid.toString()); put(j, "type", d.type.toString()); result.put(j);
        }
        return result;
    }
    private static String type(int t) {
        switch (t) {
            case AudioDeviceInfo.TYPE_BUILTIN_MIC: return "Built-in mic (address distinguishes back/bottom)";
            case AudioDeviceInfo.TYPE_WIRED_HEADSET: return "Wired headset mic";
            case AudioDeviceInfo.TYPE_USB_DEVICE: return "USB device input";
            case AudioDeviceInfo.TYPE_USB_HEADSET: return "USB headset input";
            case AudioDeviceInfo.TYPE_USB_ACCESSORY: return "USB accessory input";
            case AudioDeviceInfo.TYPE_LINE_ANALOG: return "External analog line input";
            case AudioDeviceInfo.TYPE_LINE_DIGITAL: return "Digital line input";
            case AudioDeviceInfo.TYPE_BLUETOOTH_SCO: return "Bluetooth SCO input";
            default: return "Input type " + t;
        }
    }
    private static String key(AudioDeviceInfo d) { return d.getType() + "|" + d.getAddress() + "|" + d.getProductName(); }
    private static String label(AudioDeviceInfo d) {
        return d == null ? "none / unknown" : type(d.getType()) + " · id=" + d.getId() + " · address=" + d.getAddress();
    }
    private static JSONArray intArray(int[] values) {
        JSONArray j = new JSONArray(); for (int n : values) j.put(n); return j;
    }
    private static JSONObject describe(AudioDeviceInfo d) {
        if (d == null) return null;
        JSONObject j = new JSONObject();
        put(j, "id", d.getId()); put(j, "type", d.getType()); put(j, "type_name", type(d.getType()));
        put(j, "product_name", d.getProductName().toString()); put(j, "address", d.getAddress());
        put(j, "is_source", d.isSource()); put(j, "channel_counts", intArray(d.getChannelCounts()));
        put(j, "sample_rates", intArray(d.getSampleRates())); put(j, "encodings", intArray(d.getEncodings()));
        return j;
    }
    private AudioDeviceInfo selected() {
        if (selectedKey == null) return null;
        for (AudioDeviceInfo d : devices) if (d.getId() == selectedId && key(d).equals(selectedKey)) return d;
        AudioDeviceInfo match = null;
        for (AudioDeviceInfo d : devices) if (key(d).equals(selectedKey)) {
            if (match != null) return null; // ambiguous reconnection: require explicit selection
            match = d;
        }
        if (match != null) selectedId = match.getId();
        return match;
    }
    private void refresh() {
        if (destroyed) return;
        devices = manager.getDevices(AudioManager.GET_DEVICES_INPUTS);
        inputs.setOnCheckedChangeListener(null); inputs.removeAllViews();
        RadioButton auto = new RadioButton(this); auto.setId(View.generateViewId()); auto.setText("System default (not wired proof)");
        inputs.addView(auto); if (selectedKey == null) auto.setChecked(true);
        Map<Integer, AudioDeviceInfo> choices = new HashMap<>();
        AudioDeviceInfo currentSelection = selected();
        choices.put(auto.getId(), null);
        JSONArray inventory = new JSONArray();
        for (AudioDeviceInfo d : devices) {
            inventory.put(describe(d));
            RadioButton b = new RadioButton(this); b.setId(View.generateViewId());
            b.setText(label(d) + "\n" + d.getProductName() + " · type=" + d.getType()
                    + "\nchannels=" + Arrays.toString(d.getChannelCounts()) + " rates=" + Arrays.toString(d.getSampleRates())
                    + " encodings=" + Arrays.toString(d.getEncodings()));
            inputs.addView(b); choices.put(b.getId(), d);
            if (currentSelection != null && d.getId() == currentSelection.getId()) b.setChecked(true);
            b.setEnabled(worker == null);
        }
        auto.setEnabled(worker == null);
        if (selectedKey != null && selected() == null) {
            RadioButton missing = new RadioButton(this); missing.setText("Selected input unavailable: " + selectedKey);
            missing.setEnabled(false); inputs.addView(missing); missing.setChecked(true);
        }
        inputs.setOnCheckedChangeListener((group, id) -> {
            if (!choices.containsKey(id)) return;
            AudioDeviceInfo chosen = choices.get(id);
            selectedKey = chosen == null ? null : key(chosen); selectedId = chosen == null ? -1 : chosen.getId(); showPreferred();
        });
        showPreferred(); emit("input_devices", inventory);
    }
    private void showPreferred() {
        preferred.setText("Preferred input: " + (selectedKey == null ? "System default" :
                selected() == null ? selectedKey + " [UNAVAILABLE; retained]" : label(selected())));
    }
    @Override protected void onNewIntent(Intent i) { super.onNewIntent(i); setIntent(i); handleIntent(i); }
    private void handleIntent(Intent i) {
        if (worker != null) { emit("intent_ignored", "recording"); return; }
        if (i.hasExtra("device_id")) {
            int id = i.getIntExtra("device_id", -1); boolean found = false;
            for (AudioDeviceInfo d : devices) if (d.getId() == id) { selectedKey = key(d); selectedId = d.getId(); found = true; }
            if (!found) { status.setText("Requested device_id unavailable; no recording."); emit("error", "device_id unavailable: "+id); return; }
        }
        if (i.hasExtra("source")) {
            String wanted = i.getStringExtra("source"); boolean found = false;
            for (int n = 0; n < sourceNames.length; n++) if (sourceNames[n].equals(wanted)) { sources.setSelection(n); found = true; }
            if (!found) { status.setText("Unknown source"); return; }
        }
        seconds.setText(Integer.toString(i.getIntExtra("seconds", 5)));
        strict.setChecked(i.getBooleanExtra("strict", true));
        refresh();
        if (i.getBooleanExtra("auto", false)) main.post(this::begin);
    }

    private void begin() {
        if (worker != null) return;
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1); status.setText("Grant permission, then press Start."); return;
        }
        AudioDeviceInfo target = selected();
        if (selectedKey != null && target == null) { status.setText("Selected input disappeared. Waiting for reappearance; no fallback."); return; }
        int duration;
        try { duration = Integer.parseInt(seconds.getText().toString()); } catch (Exception e) { duration = 0; }
        if (duration < 1 || duration > 300) { status.setText("Duration must be 1–300 seconds"); return; }
        final int length = duration, source = sourceValues[sources.getSelectedItemPosition()];
        final boolean strictRoute = strict.isChecked();
        running = true; start.setEnabled(false); stop.setEnabled(true); sources.setEnabled(false); strict.setEnabled(false); seconds.setEnabled(false);
        actual.setText("Actual routed input: pending"); actual.setTextColor(Color.DKGRAY);
        status.setText("Starting…");
        worker = new Thread(() -> capture(target, source, length, strictRoute), "xz1-capture");
        refresh(); worker.start();
    }

    private void routeUi(AudioDeviceInfo target, AudioDeviceInfo route, boolean mismatch) {
        main.post(() -> {
            if (destroyed) return;
            actual.setText("Actual routed input: " + label(route));
            actual.setTextColor(mismatch ? Color.RED : Color.rgb(0, 100, 0));
            if (mismatch) status.setText("ROUTE MISMATCH — not a valid recording of selected input");
        });
    }
    private void capture(AudioDeviceInfo target, int source, int duration, boolean strictRoute) {
        AudioRecord rec = null;
        RandomAccessFile wav = null;
        List<AudioEffect> ownedEffects = new ArrayList<>();
        long bytes = 0, mismatchFrames = 0, discardedFrames = 0;
        boolean routeFailed = false;
        String result = "Stopped";
        AudioRouting.OnRoutingChangedListener routing = r -> {
            AudioDeviceInfo route = r.getRoutedDevice();
            emit("routing_callback", describe(route));
            routeUi(target, route, target != null && (route == null || route.getId() != target.getId()));
        };
        try {
            final int rate = 48000;
            int min = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
            if (min <= 0) throw new IOException("Unsupported 48k mono PCM16, minBuffer=" + min);
            rec = new AudioRecord.Builder().setAudioSource(source)
                    .setAudioFormat(new AudioFormat.Builder().setSampleRate(rate).setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT).build()).setBufferSizeInBytes(Math.max(min * 2, 19200)).build();
            if (rec.getState() != AudioRecord.STATE_INITIALIZED) throw new IOException("AudioRecord not initialized");
            boolean accepted = rec.setPreferredDevice(target);
            JSONObject request = new JSONObject();
            put(request, "requested", describe(target)); put(request, "accepted", accepted);
            put(request, "preferred", describe(rec.getPreferredDevice())); put(request, "immediate_route", describe(rec.getRoutedDevice()));
            put(request, "source", source); put(request, "session", rec.getAudioSessionId()); put(request, "strict", strictRoute);
            emit("route_request", request); // route is normally null before startRecording
            if (!accepted) throw new IOException("setPreferredDevice rejected");
            // These controls cannot guarantee removal of proprietary HAL/DSP effects.
            if (AutomaticGainControl.isAvailable()) disable(AutomaticGainControl.create(rec.getAudioSessionId()), ownedEffects);
            if (NoiseSuppressor.isAvailable()) disable(NoiseSuppressor.create(rec.getAudioSessionId()), ownedEffects);
            if (AcousticEchoCanceler.isAvailable()) disable(AcousticEchoCanceler.create(rec.getAudioSessionId()), ownedEffects);
            rec.addOnRoutingChangedListener(routing, main);
            File dir = getExternalFilesDir(null); if (dir == null) dir = getFilesDir();
            File file = new File(dir, "capture-" + System.currentTimeMillis() + ".wav");
            wav = new RandomAccessFile(file, "rw"); wav.setLength(0); header(wav, 0, rate);
            emit("wav_open", file.getAbsolutePath());
            rec.startRecording();
            if (rec.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING) throw new IOException("startRecording failed");
            emit("route_after_start", describe(rec.getRoutedDevice()));
            long begin = SystemClock.elapsedRealtime(), lastUi = 0;
            int lastRoute = Integer.MIN_VALUE;
            short[] samples = new short[2400];
            byte[] encoded = new byte[samples.length * 2];
            while (running && bytes/2 < (long)rate*duration) {
                if (SystemClock.elapsedRealtime() - begin > duration*1000L + 5000) throw new IOException("Capture timed out");
                int n = rec.read(samples, 0, (int)Math.min(samples.length, (long)rate*duration-bytes/2), AudioRecord.READ_NON_BLOCKING);
                if (n < 0) throw new IOException("AudioRecord.read error " + n);
                AudioDeviceInfo route = rec.getRoutedDevice();
                boolean mismatch = route == null || (target != null && route.getId() != target.getId());
                int routeId = route == null ? -1 : route.getId();
                if (routeId != lastRoute) { emit("actual_route", describe(route)); routeUi(target, route, mismatch); lastRoute = routeId; }
                if (mismatch) {
                    if (n > 0) mismatchFrames += n;
                    // Allow initial route publication delay, but discard unverified frames.
                    if (strictRoute) {
                        if (n > 0) discardedFrames += n;
                        if (route == null && SystemClock.elapsedRealtime()-begin < 1500) { SystemClock.sleep(10); continue; }
                        routeFailed = true;
                        throw new IOException("Actual route differs or is unknown; stopped, no silent fallback");
                    }
                }
                if (n == 0) { SystemClock.sleep(10); continue; }
                double sum = 0;
                for (int i = 0; i < n; i++) {
                    int s = samples[i]; sum += (double)s*s;
                    encoded[i*2] = (byte)s; encoded[i*2+1] = (byte)(s >> 8);
                }
                wav.write(encoded, 0, n*2); bytes += n*2;
                long now = SystemClock.elapsedRealtime();
                if (now-lastUi >= 200) {
                    lastUi = now;
                    double rms = Math.sqrt(sum/n)/32768.0;
                    JSONObject reading = new JSONObject();
                    put(reading, "rms", rms); put(reading, "frames_written", bytes/2); put(reading, "route", describe(route));
                    put(reading, "mismatch", mismatch); emit("meter", reading);
                    final String display = rms > 0 ? String.format(Locale.US, "RMS %.6f  |  %.1f dBFS", rms, 20*Math.log10(rms)) : "RMS 0 | silence";
                    main.post(() -> { if (!destroyed) meter.setText(display); });
                }
            }
            result = mismatchFrames > 0 && !strictRoute ? "Saved with ROUTE MISMATCH — inspect events" :
                    bytes/2 >= (long)rate*duration ? "Saved; confirm signal origin with controls" : "Stopped; partial WAV saved";
        } catch (Exception e) {
            result = "ERROR: " + e.getMessage(); emit("capture_error", result);
        } finally {
            running = false;
            if (rec != null) {
                try { rec.removeOnRoutingChangedListener(routing); } catch (Exception ignored) {}
                try { rec.stop(); } catch (Exception ignored) {}
                for (AudioEffect effect : ownedEffects) effect.release();
                rec.release();
            }
            if (wav != null) {
                try { header(wav, bytes, 48000); wav.close(); } catch (Exception e) { result += "; WAV finalize error: "+e; }
            }
            JSONObject end = new JSONObject();
            put(end, "result", result); put(end, "frames_written", bytes/2); put(end, "mismatch_frames", mismatchFrames);
            put(end, "discarded_unverified_frames", discardedFrames); put(end, "route_failed", routeFailed);
            emit("capture_end", end);
            final String summary = result;
            main.post(() -> {
                worker = null;
                if (destroyed) return;
                start.setEnabled(true); stop.setEnabled(false); sources.setEnabled(true); strict.setEnabled(true); seconds.setEnabled(true);
                status.setText(summary); actual.append(" [last observed; stopped]"); refresh();
            });
        }
    }
    private void disable(AudioEffect effect, List<AudioEffect> owned) {
        if (effect == null) return;
        owned.add(effect);
        JSONObject j = new JSONObject();
        put(j, "effect", effect.getDescriptor().name); put(j, "has_control", effect.hasControl());
        put(j, "disable_result", effect.setEnabled(false)); put(j, "enabled_after", effect.getEnabled());
        emit("effect_control", j);
    }
    private static void header(RandomAccessFile f, long size, int rate) throws IOException {
        ByteBuffer b = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN);
        b.put(new byte[]{'R','I','F','F'}).putInt((int)(36+size)).put(new byte[]{'W','A','V','E','f','m','t',' '})
                .putInt(16).putShort((short)1).putShort((short)1).putInt(rate).putInt(rate*2)
                .putShort((short)2).putShort((short)16).put(new byte[]{'d','a','t','a'}).putInt((int)size);
        f.seek(0); f.write(b.array()); f.seek(44+size);
    }
    @Override protected void onStop() {
        running = false; super.onStop(); // foreground-only, no hidden/background recording
    }
    @Override protected void onDestroy() {
        destroyed = true; running = false;
        manager.unregisterAudioDeviceCallback(deviceCallback);
        manager.unregisterAudioRecordingCallback(recordingCallback);
        // Worker finalization can still write evidence. Close only after it has completed.
        Thread w = worker;
        new Thread(() -> {
            if (w != null) try { w.join(7000); } catch (InterruptedException ignored) {}
            synchronized (this) { if (events != null) { events.close(); events = null; } }
        }).start();
        super.onDestroy();
    }
}
