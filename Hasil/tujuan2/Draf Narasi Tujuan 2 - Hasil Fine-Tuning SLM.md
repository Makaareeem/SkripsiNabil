# Draf Narasi Tujuan 2 Hasil Fine-Tuning Small Language Model

## Petunjuk status evidensi

Draf kerja ini menggunakan penanda berikut agar fakta hasil eksekusi tidak tercampur dengan penafsiran peneliti.

- **[HASIL]**: angka atau fakta yang diperoleh langsung dari notebook, berkas konfigurasi, atau berkas hasil penelitian.
- **[INTERPRETASI]**: penafsiran peneliti yang diturunkan dari hasil, tetapi bukan keluaran langsung program.
- **[ASUMSI]**: dugaan yang masuk akal dan didukung literatur, tetapi belum diuji secara langsung pada eksperimen ini.
- **[PERLU DILENGKAPI]**: artefak atau hasil yang belum tersedia, tidak konsisten, atau masih memerlukan perbaikan kode.

Penanda tersebut dapat dihapus setelah seluruh temuan diverifikasi dan narasi dipindahkan ke naskah akhir.

## 4.2 Hasil Fine-Tuning Small Language Model

Tahap fine-tuning bertujuan mengadaptasi dua SLM terpilih agar mampu menghasilkan jawaban berbahasa Indonesia berdasarkan konteks publikasi statistik BPS. Dengan demikian, hasil pada bagian ini tidak dimaksudkan untuk mengukur kualitas retrieval ataupun kinerja sistem RAG secara utuh. Seluruh evaluasi pada Tujuan 2 menggunakan *oracle context*, yaitu konteks yang telah diketahui memuat evidensi jawaban. Ruang lingkup ini penting ditegaskan karena peningkatan skor pada bagian ini menunjukkan kemampuan model memanfaatkan konteks yang benar, mengikuti instruksi, dan menghasilkan format respons yang dipelajari; kemampuan menemukan konteks yang benar baru diuji pada Tujuan 3. **[HASIL dan batas inferensi]**

Fine-tuning dilakukan terhadap Gemma-2-2B-Instruct dan Llama-3.2-3B-Instruct. Kedua model dilatih dengan *supervised instruction tuning* menggunakan QLoRA. QLoRA mempertahankan bobot dasar dalam keadaan beku dan terkuantisasi 4-bit, kemudian hanya memperbarui adaptor berperingkat rendah. Rancangan tersebut sejalan dengan prinsip QLoRA yang menekan kebutuhan memori tanpa memperbarui seluruh bobot model ([Dettmers et al., 2023](https://papers.neurips.cc/paper_files/paper/2023/file/1feb87871436031bdc0f2beaa62a049b-Paper-Conference.pdf)) dan LoRA yang mengadaptasi model melalui matriks berperingkat rendah ([Hu et al., 2021](https://arxiv.org/abs/2106.09685)). Dalam penelitian ini, proporsi parameter yang dilatih hanya 0,79% pada Gemma-2 dan 0,75% pada Llama-3.2. **[HASIL]**

### 4.2.1 Hasil Dataset Fine-Tuning

#### Pembentukan korpus dan unit konteks

Korpus sumber terdiri atas 47 publikasi resmi BPS periode 2022–2025 yang mencakup 15.159 halaman. Ekstraksi menghasilkan 34.464.824 karakter mentah, kemudian proses pembersihan menyisakan 29.973.328 karakter atau mengurangi 13,03% karakter. Reduksi tersebut berasal dari normalisasi Unicode, perbaikan pemenggalan kata, penghapusan tag `<br>`, marker gambar, dan watermark URL BPS, serta normalisasi spasi. Hasil ini tidak berarti 13,03% informasi substantif dibuang, sebab aturan pembersihan dirancang untuk menghapus artefak ekstraksi sambil mempertahankan struktur Markdown. Namun, persentase reduksi tetap perlu dibaca bersama indikator halaman kosong dan halaman berkarakter rendah karena beberapa publikasi memiliki elemen visual dan tabel yang dominan. **[HASIL; INTERPRETASI pada makna reduksi]**

Teks bersih direkonstruksi menjadi 11.571 *section* berdasarkan penanda struktur, antara lain heading Markdown, bab, penomoran subbab, lampiran, daftar isi, daftar tabel, daftar gambar, dan bagian khusus. Setiap *section* kemudian dipecah tanpa melintasi batas strukturnya menggunakan `RecursiveCharacterTextSplitter`, dengan ukuran 2.000 karakter dan *overlap* 200 karakter. Proses tersebut menghasilkan 22.603 *chunk*. Komposisinya sangat didominasi *text-only* sebanyak 21.295 *chunk* (94,21%), sedangkan 643 *chunk* dikategorikan *figure-rich*, 307 *table-rich*, 152 *mixed-rich*, serta 206 *chunk* navigasi daftar tabel/gambar. **[HASIL]**

Dominasi *text-only* sesuai dengan batasan penelitian yang tidak menggunakan isi sel tabel dan nilai visual sebagai sumber jawaban. Akan tetapi, hasil eksplorasi dataset memperlihatkan bahwa residu tabel tetap menjadi masalah kualitas terbesar. Artinya, klasifikasi struktur pada tahap awal belum sepenuhnya mampu mencegah baris tabel yang terlinearisasi masuk sebagai narasi. Temuan ini menjelaskan mengapa pemeriksaan pada tingkat pasangan pertanyaan–jawaban tetap diperlukan walaupun penyaringan sudah dilakukan pada tingkat dokumen, *section*, dan *chunk*. **[INTERPRETASI berbasis hasil penyaringan]**

#### Desain prompt pembentukan pasangan pertanyaan–jawaban

Pasangan instruksi dan jawaban dibentuk secara sintetis menggunakan `deepseek-v4-flash`. Pendekatan ini merupakan bentuk *knowledge distillation*: model yang lebih besar berperan sebagai *teacher* untuk membentuk data instruksi bagi SLM sebagai *student*. Praktik pembentukan data instruksi sintetis memiliki landasan pada Self-Instruct, yang membangkitkan instruksi lalu menyaring keluaran yang tidak valid atau terlalu mirip sebelum fine-tuning ([Wang et al., 2023](https://aclanthology.org/2023.acl-long.754/)). **[HASIL untuk implementasi; dasar literatur untuk pendekatan]**

Prompt sistem pada kode tidak hanya meminta model membuat pertanyaan dan jawaban, tetapi menetapkan enam tahap internal. Model diminta memilih subtopik, memilih satu sampai tiga kutipan evidensi yang ditemukan dalam sumber, menyusun instruksi spesifik, membentuk CoT maksimal dua kalimat, menulis jawaban yang hanya didukung evidensi, serta melakukan validasi silang atas kutipan, angka, satuan, wilayah, jenis pertanyaan, dan keunikan subtopik. Prompt juga melarang penggunaan baris tabel terlinearisasi, angka turunan yang tidak memiliki dua angka sumber eksplisit, dan frasa meta seperti “konteks ini” atau “dokumen ini”. Contoh benar dan salah ditambahkan untuk memperjelas batas perilaku yang diinginkan. **[HASIL dari kode prompt]**

Empat pola penalaran digunakan untuk memperluas cakupan perilaku model, yaitu: (1) pembacaan literal untuk `factual_retrieval` dan `source_navigation`; (2) pemahaman konsep untuk `definition_clarification` dan `methodology_explanation`; (3) integrasi evidensi untuk `trend_interpretation` dan `causal_reasoning`; serta (4) penalaran analitis untuk `comparative_analysis` dan `multi_source_synthesis`. Pola kelima menghasilkan `document_overview`. Pembagian ini membuat dataset tidak hanya melatih pengambilan fakta, tetapi juga definisi, metodologi, interpretasi, perbandingan, dan sintesis. **[HASIL dari kode]**

Rancangan tersebut mengadaptasi gagasan RAFT karena respons dilatih untuk mengutip evidensi relevan dan menjawab dalam skenario *open-book*. RAFT menunjukkan manfaat kutipan verbatim dan respons bergaya CoT dalam adaptasi model untuk RAG domain khusus ([Zhang et al., 2024](https://arxiv.org/abs/2403.10131)). Namun, implementasi penelitian ini belum dapat disebut RAFT penuh karena seluruh record hanya menggunakan konteks relevan dan tidak menyertakan *distractor documents*, padahal RAFT secara eksplisit melatih model mengabaikan dokumen yang tidak membantu. Oleh karena itu, istilah yang lebih presisi untuk naskah adalah **retrieval-aware instruction tuning yang diadaptasi dari RAFT**, bukan implementasi RAFT identik. **[HASIL dan INTERPRETASI metodologis]**

CoT pada target menggunakan pola singkat “Teks menyatakan ... Karena itu ...”. Penggunaan langkah penalaran memiliki dasar pada penelitian CoT ([Wei et al., 2022](https://proceedings.neurips.cc/paper/2022/hash/9d5609613524ecf4f15af0f7b31abca4-Abstract-Conference.html)), tetapi hasil penelitian tersebut terutama menunjukkan manfaat pada model yang cukup besar dan tugas penalaran tertentu. Pada penelitian ini, CoT lebih tepat dipahami sebagai format evidensi terstruktur yang menghubungkan kutipan dan jawaban, bukan bukti bahwa proses penalaran internal model menjadi benar. **[INTERPRETASI; kehati-hatian klaim]**

#### Hasil generasi, penyaringan, dan dataset akhir

Proses generasi menyeleksi 1.069 dari 7.535 *section* yang direkonstruksi pada tahap tersebut. Proses berhenti ketika saldo API generator habis, setelah menghasilkan 12.261 record dari 29 dokumen. Dengan demikian, hanya 61,70% dari 47 dokumen korpus yang terwakili dalam dataset sintetis. Sebanyak 17 permintaan tercatat gagal diurai, sementara proses menghasilkan total 32.029.092 token, terdiri atas 26.502.232 token prompt dan 5.526.860 token keluaran; 12.173.184 token prompt tercatat sebagai token *cache* dengan *cache hit rate* 45,93%. **[HASIL]**

Eksplorasi awal menunjukkan bahwa data mentah mencakup 11.498 record QA dan 763 ringkasan. Masalah yang paling sering terdeteksi adalah CoT tanpa kutipan literal (7.747 record), angka jawaban yang tidak terlacak pada konteks (3.015), residu notasi tabel (1.915), CoT yang gagal diverifikasi (422), inkonsistensi terminologi (331), kemiripan pertanyaan dan jawaban yang terlalu tinggi (326), kebocoran meta-referensi (183), dan duplikasi persis instruksi (106). Angka-angka eksplorasi ini adalah indikator calon masalah dan dapat tumpang tindih; karena itu jumlahnya tidak boleh dijumlahkan sebagai total record bermasalah. **[HASIL dan penjelasan cara baca]**

Pembersihan bertingkat membuang 2.911 record atau 23,74% data mentah. Alasan yang tercatat meliputi residu tabel pada 1.896 record, *high OCR noise* pada 749 record, *near duplicate* pada 232 record, campuran bahasa Inggris pada 80 record, dan instruksi yang meminta pembacaan tabel secara langsung pada 40 record. Satu record dapat memiliki lebih dari satu flag sehingga jumlah alasan pembuangan dapat melebihi jumlah record yang dibuang. Sebanyak 9.350 record atau 76,26% data mentah lolos *hard gate*. **[HASIL]**

Dataset akhir mencakup 29 dokumen, 628 *section*, dan tiga tahun terbit: 3.718 record dari publikasi tahun 2023, 3.015 dari 2024, dan 2.617 dari 2025. Lima dokumen dengan kontribusi terbesar menyumbang 32,57% seluruh record. Komposisi ini menunjukkan ketimpangan moderat pada sumber dokumen. Model berpotensi lebih sering mempelajari gaya, topik, dan pola penyajian lima dokumen tersebut dibandingkan publikasi lain yang kontribusinya lebih kecil. Pernyataan terakhir merupakan risiko yang masuk akal, tetapi belum diuji dengan evaluasi generalisasi per dokumen. **[HASIL; ASUMSI untuk dampak terhadap model]**

Distribusi sembilan sub-tugas pada dataset akhir relatif merata, dengan jumlah tertinggi pada `definition_clarification` (1.344) dan terendah pada `document_overview` (515). Entropi strata ternormalisasi sebesar 0,9845 dan koefisien Gini sebesar 0,1357 mendukung kesimpulan bahwa distribusi jenis pertanyaan cukup seimbang. Pada sisi keragaman bahasa, `distinct-1` sebesar 0,0515, `distinct-2` sebesar 0,2752, *Self-BLEU* sebesar 0,6192, dan rerata kemiripan kosinus antarinstruksi sebesar 0,282. Lima pola pembuka teratas mencakup 19,71% instruksi; pola “apa yang dimaksud” sendiri mencakup 10,12%. Hasil ini menunjukkan cakupan jenis tugas yang seimbang, tetapi pola perumusan instruksi masih cukup terstruktur dan berulang. **[HASIL; INTERPRETASI]**

Kemiripan semantik antara jawaban dan konteks memiliki rerata 0,8155 dan median 0,8635. Sebanyak 600 dari 9.350 record (6,42%) memiliki skor di bawah 0,5. Skor terendah dan rerata paling rendah muncul pada `source_navigation`, yang wajar karena jawaban tipe ini sering hanya menyebut nomor atau lokasi tabel, sedangkan konteks dapat berisi judul yang lebih panjang. Oleh sebab itu, kemiripan rendah tidak otomatis membuktikan jawaban salah; metrik tersebut berfungsi sebagai alat penyaringan kandidat untuk pemeriksaan manual. **[HASIL; INTERPRETASI]**

Skor kualitas komposit `track_a_score` pada dataset akhir, ketika dihitung langsung dari `train.csv`, `val.csv`, dan `test.csv`, memiliki rerata 0,9682; sebanyak 7.905 record memperoleh skor sempurna 1,0. Rerata `numeric_score` adalah 0,9303, tetapi 1.277 record masih memiliki nilai di bawah 1 dan 400 record memiliki nilai di bawah 0,5. Hal ini berarti pembersihan tidak menjadikan kesesuaian angka sebagai *hard gate*. Record dengan angka yang belum seluruhnya terlacak masih dipertahankan melalui mekanisme penalti. Keputusan ini mempertahankan cakupan data, tetapi juga menyisakan risiko supervisi numerik yang keliru. **[HASIL; INTERPRETASI]**

Perlu dibedakan bahwa angka `track_a_score` 0,9518 pada notebook visualisasi dihitung atas 12.261 record sebelum *hard gate*. Nilai itu menggambarkan kualitas data mentah setelah pemberian skor, bukan kualitas 9.350 record final. Untuk subbagian hasil dataset akhir, angka yang lebih tepat digunakan adalah 0,9682. **[HASIL audit kode]**

Dataset dibagi pada tingkat *section*, bukan tingkat record, dengan seed 42. Hasil akhirnya terdiri atas 6.516 data latih (69,69%), 1.043 validasi (11,16%), dan 1.791 uji (19,16%), dengan nol *section* yang muncul pada lebih dari satu subset. Perbedaan proporsi aktual dari target 70:10:20 terjadi karena unit pengacakan adalah *section* yang memiliki jumlah record berbeda-beda. Pilihan ini lebih kuat daripada pemisahan tingkat record karena record dalam satu *section* dapat berbagi potongan konteks yang tumpang tindih; memisahkannya ke train dan test akan membuat skor evaluasi terlalu optimistis. **[HASIL; INTERPRETASI metodologis]**

Walaupun 80 record berbahasa Inggris dibuang, pemeriksaan ulang berkas final menemukan sedikitnya 14 instruksi yang masih diawali pola pertanyaan bahasa Inggris, misalnya “What ...” dan “How ...”. Jumlah tersebut kecil (sekitar 0,15%), tetapi bertentangan dengan klaim bahwa dataset sepenuhnya berbahasa Indonesia. Record tersebut perlu diperiksa dan, bila fokus penelitian memang monolingual, dibersihkan sebelum eksperimen final diulang. **[HASIL audit tambahan; PERLU DILENGKAPI]**

**Tabel ringkasan dataset akhir**

| Aspek | Hasil |
|---|---:|
| Record mentah | 12.261 |
| Record dibuang | 2.911 (23,74%) |
| Record akhir | 9.350 (76,26%) |
| Dokumen terwakili | 29 dari 47 |
| Section unik | 628 |
| Train | 6.516 |
| Validasi | 1.043 |
| Uji | 1.791 |
| Rerata track_a_score final | 0,9682 |
| Rerata numeric_score final | 0,9303 |
| Rerata IndoBERT similarity jawaban–konteks | 0,8155 |
| Section bocor antar-split | 0 |

Visual yang paling relevan untuk subbagian ini adalah funnel pembentukan dataset, cakupan 29 dari 47 dokumen, alasan pembuangan record, distribusi sub-tugas, distribusi `track_a_score`, keragaman instruksi, dan pembagian train–validasi–test. Grafik ekstraksi 47 dokumen tetap dapat ditampilkan secara ringkas sebagai konteks, tetapi tidak perlu mendominasi subbagian Tujuan 2.

### 4.2.2 Hasil Pelatihan

#### Format input dan target pelatihan

Setiap record diubah ke format percakapan bawaan masing-masing tokenizer. Giliran pengguna berisi system prompt, blok `Konteks:`, dan `Pertanyaan:`. Giliran asisten berisi CoT, dua baris kosong, lalu jawaban akhir. Llama-3.2 menempatkan system prompt pada peran `system`, sedangkan Gemma-2 memasukkannya pada awal pesan pengguna karena template yang digunakan tidak memiliki peran system bawaan. Konsistensi format antara pelatihan dan inferensi dijaga dengan menggunakan prompt yang sama pada tahap pembangkitan prediksi. **[HASIL dari kode]**

System prompt berbunyi: “Anda adalah asisten yang menjawab pertanyaan seputar publikasi statistik BPS berdasarkan konteks yang diberikan. Kutip bagian konteks yang relevan sebelum menjawab.” Formulasi ini selaras dengan target data yang selalu berisi CoT berkutip dan jawaban akhir. Konsekuensinya, model tidak hanya dilatih menemukan jawaban, tetapi juga meniru gaya respons dua bagian. **[HASIL; INTERPRETASI]**

Loss dihitung hanya pada token respons melalui `train_on_responses_only`. Token system prompt, konteks, dan pertanyaan berfungsi sebagai kondisi input, tetapi tidak menjadi target prediksi. Pilihan ini tepat untuk menghindari penggunaan kapasitas adaptor guna menyalin kembali prompt dan konteks. Delimiter pengguna dan asisten divalidasi sebelum pelatihan agar *masking* tidak bergeser. **[HASIL; INTERPRETASI teknis]**

Analisis panjang token menghasilkan rerata 266,6 token untuk Gemma-2 dan 377,9 token untuk Llama-3.2. Panjang maksimum masing-masing adalah 915 dan 1.104 token. Oleh karena itu, `max_seq_length` ditetapkan 1.024 untuk Gemma-2 dan 1.536 untuk Llama-3.2, yaitu kandidat standar terkecil yang tetap menampung contoh terpanjang. Dengan konfigurasi ini, tidak ada contoh data latih yang seharusnya terpotong pada tahap persiapan. **[HASIL]**

Perbedaan panjang token tidak menunjukkan bahwa konteks Llama-3.2 secara substantif lebih panjang. Record sumbernya sama; perbedaan terutama berasal dari tokenisasi dan format chat yang berbeda. **[INTERPRETASI]**

#### Konfigurasi QLoRA

| Parameter | Gemma-2-2B | Llama-3.2-3B |
|---|---:|---:|
| Model dasar | `unsloth/gemma-2-2b-it-bnb-4bit` | `unsloth/Llama-3.2-3B-Instruct-bnb-4bit` |
| max_seq_length | 1.024 | 1.536 |
| LoRA rank / alpha / dropout | 16 / 32 / 0,1 | 16 / 32 / 0,1 |
| Modul target | q, k, v, o, gate, up, down projection | q, k, v, o, gate, up, down projection |
| Batch per device | 4 | 2 |
| Gradient accumulation | 4 | 8 |
| Batch efektif | 16 | 16 |
| Learning rate | 2 × 10⁻⁵, konstan | 2 × 10⁻⁵, konstan |
| Epoch / total step | 3 / 1.224 | 3 / 1.224 |
| Optimizer | paged_adamw_8bit | paged_adamw_8bit |
| Weight decay / max grad norm | 0,01 / 0,3 | 0,01 / 0,3 |
| Presisi komputasi | fp16 | fp16 |
| Packing | Tidak | Tidak |
| Seed | 42 | 42 |

Kedua model menggunakan target modul yang sama agar ruang adaptasi mencakup proyeksi atensi dan MLP. Gemma-2 melatih 20.766.720 dari 2.635.108.608 parameter (0,79%), sedangkan Llama-3.2 melatih 24.313.856 dari 3.237.063.680 parameter (0,75%). Hasil ini menegaskan efisiensi parameter QLoRA: kurang dari satu persen parameter diperbarui, sementara bobot dasar tetap beku. **[HASIL]**

Uji VRAM pada persiapan menunjukkan Gemma-2 dapat menjalankan kandidat batch 4 dengan estimasi reservasi 14,31 GB, sedangkan kandidat 8 gagal; Llama-3.2 dapat menjalankan batch 2 dengan estimasi 11,97 GB, sedangkan batch 4 gagal. Batch efektif kemudian disamakan menjadi 16 melalui *gradient accumulation*. Kesetaraan batch efektif mengurangi satu sumber perbedaan optimisasi antarmodel, walaupun panjang urutan, jumlah parameter, dan penempatan model pada GPU tetap berbeda. **[HASIL; INTERPRETASI]**

#### Dinamika loss dan efisiensi pelatihan

Gemma-2 menyelesaikan 1.224 langkah dalam 14.399,53 detik atau sekitar 4,00 jam, dengan *training loss* agregat 0,4376 dan *validation loss* terakhir 0,4405. Llama-3.2 menyelesaikan jumlah langkah yang sama dalam 20.697,91 detik atau sekitar 5,75 jam, dengan *training loss* agregat 0,3609 dan *validation loss* terakhir 0,3404. Laju pelatihan Gemma-2 adalah 0,085 langkah per detik, sedangkan Llama-3.2 sebesar 0,059 langkah per detik. **[HASIL]**

Kurva kedua model menunjukkan penurunan loss validasi yang konsisten. Pada Gemma-2, loss validasi turun dari 0,5865 pada langkah 50 menjadi 0,4405 pada langkah 1.200, atau turun sekitar 24,9%. Pada Llama-3.2, loss validasi turun dari 0,4868 menjadi 0,3404, atau turun sekitar 30,1%. Setelah kurang lebih langkah 800, penurunan Gemma-2 menjadi sangat kecil dan sempat berfluktuasi, sedangkan Llama-3.2 masih turun perlahan. Tidak ditemukan lonjakan loss validasi yang berkelanjutan sampai akhir pelatihan. **[HASIL]**

Pola tersebut menunjukkan konvergensi dan belum memberikan bukti kuat tentang overfitting berat. Namun, selisih antara loss pelatihan pada log terakhir dan loss validasi tetap melebar karena loss pelatihan terus turun saat loss validasi mulai mendatar. Oleh sebab itu, tiga epoch dapat dipertahankan sebagai konfigurasi akhir, tetapi klaim “tidak terjadi overfitting” sebaiknya dihindari. Pernyataan yang lebih tepat adalah “tidak ditemukan divergensi validasi, tetapi terdapat indikasi kejenuhan dan celah generalisasi ringan pada bagian akhir pelatihan.” **[INTERPRETASI]**

Llama-3.2 mencapai loss lebih rendah daripada Gemma-2, tetapi nilai loss lintas arsitektur tidak dapat langsung dipakai untuk menyatakan Llama lebih baik karena tokenizer, panjang urutan, dan distribusi token berbeda. Pemilihan model terbaik harus didasarkan pada evaluasi keluaran pada data uji, bukan perbandingan loss mentah antarmodel. **[INTERPRETASI metodologis]**

Pada inferensi 1.791 butir, Gemma-2 dasar memerlukan 5.001,02 detik dan Gemma-2 fine-tuned 3.766,71 detik, atau masing-masing sekitar 2,79 dan 2,10 detik per butir. Llama-3.2 dasar memerlukan 11.857,84 detik dan versi fine-tuned 11.741,18 detik, atau sekitar 6,62 dan 6,56 detik per butir. Perbandingan waktu base dan fine-tuned dalam model yang sama menunjukkan adaptor tidak menambah latensi yang berarti, bahkan keluaran Gemma fine-tuned selesai lebih cepat. Namun, durasi juga dipengaruhi panjang keluaran: model dasar Gemma menghasilkan jawaban dengan persentil ke-95 202,5 kata, sedangkan versi fine-tuned 129 kata. **[HASIL; INTERPRETASI]**

Waktu Gemma-2 dan Llama-3.2 tidak boleh dibandingkan secara langsung karena eksperimen Gemma menggunakan dua GPU, sedangkan Llama menggunakan satu GPU. Selain itu, mekanisme pemuatan model pada beberapa GPU bukan pengujian efisiensi perangkat lokal yang terkontrol. Klaim efisiensi deployment harus menggunakan hasil Tujuan 3 pada perangkat dan konfigurasi yang sama. **[HASIL dan batas inferensi]**

Visual utama untuk subbagian pelatihan adalah distribusi panjang token, tabel konfigurasi QLoRA, kurva training–validation loss, proporsi parameter yang dilatih, dan durasi pelatihan. Grafik inferensi dapat disertakan dengan catatan bahwa perbandingan lintas model tidak setara.

### 4.2.3 Hasil Automatic Evaluation

#### Konfigurasi evaluasi dan definisi metrik

Evaluasi otomatis dilakukan pada 1.791 butir uji yang berasal dari *section* berbeda dengan data latih. Untuk setiap model, kondisi dasar dan fine-tuned menerima konteks, pertanyaan, system prompt, dan konfigurasi generasi yang sama. Prediksi dibangkitkan secara deterministik dengan *greedy decoding*, `do_sample=False`, batch 8, dan maksimum 512 token baru. Jawaban acuan yang dibandingkan bukan hanya jawaban final, melainkan gabungan CoT dan jawaban. **[HASIL]**

Empat skor dihitung, yaitu kesesuaian angka yang pada kode diberi nama EM, Token F1, ROUGE-L, dan IndoBERTScore. Token F1 menangkap irisan kata, ROUGE-L menangkap urutan bersama terpanjang, dan IndoBERTScore mencocokkan representasi kontekstual token. BERTScore memang dirancang untuk menangkap kemiripan semantik yang tidak tertangkap oleh kecocokan permukaan ([Zhang et al., 2020](https://arxiv.org/abs/1904.09675)). Walaupun demikian, ketiga metrik tetap mengukur kedekatan terhadap target sintetis dan tidak secara mandiri membuktikan kebenaran faktual. **[HASIL; INTERPRETASI]**

Istilah Exact Match dalam hasil perlu dikoreksi. Kode yang menghasilkan `summary_metrics.csv` mengekstrak seluruh angka pada jawaban acuan dan memberikan skor 1 jika himpunan angka acuan merupakan subset dari angka prediksi. Soal tanpa angka diberi `None` dan tidak masuk rata-rata. Dengan demikian, metrik ini hanya dihitung pada 1.244 dari 1.791 butir (69,46%) dan tidak menuntut kesamaan teks ataupun melarang angka tambahan. Nama yang lebih tepat adalah **akurasi cakupan angka acuan** atau **numeric subset accuracy**, bukan Exact Match konvensional. **[HASIL audit kode]**

#### Perbandingan skor keseluruhan

| Model | Kondisi | Cakupan angka | Token F1 | ROUGE-L | IndoBERTScore |
|---|---|---:|---:|---:|---:|
| Gemma-2-2B | Base | 0,5892 | 0,4500 | 0,3701 | 0,7651 |
| Gemma-2-2B | Fine-tuned | 0,7259 | 0,7236 | 0,6519 | 0,8911 |
| Llama-3.2-3B | Base | 0,5281 | 0,4110 | 0,3356 | 0,7435 |
| Llama-3.2-3B | Fine-tuned | 0,7066 | 0,7215 | 0,6525 | 0,8899 |

Gemma-2 mengalami peningkatan absolut 0,1367 pada cakupan angka, 0,2735 pada Token F1, 0,2818 pada ROUGE-L, dan 0,1260 pada IndoBERTScore. Secara relatif terhadap skor awal, peningkatan tersebut setara dengan 23,19%, 60,78%, 76,15%, dan 16,47%. Llama-3.2 meningkat 0,1785, 0,3105, 0,3168, dan 0,1464, atau secara relatif 33,79%, 75,54%, 94,41%, dan 19,70%. **[HASIL]**

Peningkatan tidak hanya terlihat pada rerata. Untuk Gemma-2, fine-tuning menaikkan Token F1 pada 96,76% butir dan IndoBERTScore pada 95,64% butir. Untuk Llama-3.2, persentasenya masing-masing 98,16% dan 96,26%. Pada metrik cakupan angka, perubahan lebih jarang karena 73,47% butir numerik Gemma dan 67,52% butir numerik Llama bernilai seri; kondisi fine-tuned tetap lebih sering membaik daripada memburuk. **[HASIL]**

Uji Wilcoxon berpasangan pada notebook visualisasi menghasilkan nilai p di bawah 0,001 untuk seluruh kombinasi model dan metrik. Hasil tersebut mendukung penolakan hipotesis tidak ada perubahan skor setelah fine-tuning. Akan tetapi, ukuran sampel yang besar membuat nilai p mudah menjadi sangat kecil; besaran peningkatan dan proporsi butir yang membaik lebih informatif untuk menilai relevansi praktis. **[HASIL; INTERPRETASI statistik]**

Kode menamai `proporsi menang − proporsi kalah` sebagai Cliff's delta. Penamaan ini tidak tepat karena Cliff's delta standar membandingkan seluruh pasangan lintas dua kelompok, sedangkan desain penelitian bersifat berpasangan per butir. Nilai yang dihitung lebih tepat disebut **indeks menang–kalah berpasangan**. Untuk naskah, disarankan melaporkan proporsi membaik/seri/memburuk dan, bila memerlukan ukuran efek Wilcoxon, menghitung *matched-pairs rank-biserial correlation*. **[HASIL audit statistik; PERLU DILENGKAPI]**

#### Hasil menurut jenis pertanyaan

Peningkatan Token F1 terjadi pada seluruh sembilan sub-tugas. Pada Gemma-2, peningkatan terbesar terjadi pada `source_navigation` (+0,3725), `factual_retrieval` (+0,3284), dan `methodology_explanation` (+0,2953). Peningkatan terkecil terjadi pada `multi_source_synthesis` (+0,1678) dan `comparative_analysis` (+0,1962). Pada Llama-3.2, pola yang sama muncul: `source_navigation` (+0,3892), `factual_retrieval` (+0,3810), dan `methodology_explanation` (+0,3421) menjadi tiga peningkatan terbesar, sedangkan `comparative_analysis` (+0,2202) dan `multi_source_synthesis` (+0,2286) berada di bagian bawah. **[HASIL]**

| Sub-tugas | Gemma F1 base → FT | Delta | Llama F1 base → FT | Delta |
|---|---:|---:|---:|---:|
| Source navigation | 0,3835 → 0,7560 | +0,3725 | 0,3685 → 0,7576 | +0,3892 |
| Factual retrieval | 0,4729 → 0,8013 | +0,3284 | 0,4231 → 0,8041 | +0,3810 |
| Methodology explanation | 0,4231 → 0,7185 | +0,2953 | 0,3735 → 0,7156 | +0,3421 |
| Definition clarification | 0,4389 → 0,7111 | +0,2722 | 0,4138 → 0,7054 | +0,2916 |
| Document overview | 0,4557 → 0,7143 | +0,2587 | 0,4390 → 0,6909 | +0,2519 |
| Trend interpretation | 0,4837 → 0,7107 | +0,2270 | 0,4264 → 0,7167 | +0,2903 |
| Causal reasoning | 0,4716 → 0,6962 | +0,2246 | 0,4079 → 0,6865 | +0,2786 |
| Comparative analysis | 0,4907 → 0,6870 | +0,1962 | 0,4665 → 0,6868 | +0,2202 |
| Multi-source synthesis | 0,4928 → 0,6607 | +0,1678 | 0,4348 → 0,6634 | +0,2286 |

Performa ini memperlihatkan bahwa fine-tuning paling efektif pada tugas dengan target yang relatif eksplisit: menemukan fakta atau lokasi pembahasan. Kenaikan yang lebih kecil pada perbandingan dan sintesis dapat menunjukkan bahwa tugas tersebut membutuhkan penggabungan evidensi dan pengendalian keluaran yang lebih kompleks. Penjelasan ini masuk akal, tetapi masih merupakan interpretasi; untuk membuktikannya diperlukan analisis kesalahan kualitatif yang mengodekan jenis kegagalan pada tiap sub-tugas. **[INTERPRETASI dan ASUMSI]**

Contoh pada `source_navigation` mendukung perubahan perilaku tersebut. Pada pertanyaan tentang lokasi “Tabel 3.1 Capaian IPM Sepuluh Provinsi dengan Pertumbuhan IPM Tercepat, 2023”, Llama dasar menjawab bahwa informasi nomor tabel tidak tersedia, sedangkan Llama fine-tuned mengutip judul tabel dan memberikan nomor 3.1 secara tepat sama dengan acuan. Contoh Gemma menunjukkan pola serupa pada Tabel 2.42. **[HASIL kualitatif dari prediksi]**

Namun, fine-tuning tidak selalu memperbaiki jawaban. Pada satu pertanyaan berbahasa Inggris tentang komponen *final demand*, Llama dasar menyebut seluruh komponen secara lebih rinci, sedangkan versi fine-tuned menggunakan terjemahan yang lebih umum sehingga Token F1 turun dari 0,592 menjadi 0,286. Pada Gemma, satu jawaban navigasi sumber kehilangan judul tabel berbahasa Inggris meskipun tetap memberikan nomor yang benar, sehingga F1 turun. Contoh tersebut menunjukkan bahwa peningkatan rerata tidak menghapus kasus regresi, terutama pada data dwibahasa dan target yang menuntut terminologi spesifik. **[HASIL kualitatif]**

Rerata panjang prediksi juga berubah mendekati acuan. Pada Gemma, median panjang jawaban berubah dari 37 kata pada model dasar menjadi 63 kata setelah fine-tuning, mendekati median acuan 64 kata. Pada Llama, median berubah dari 38 menjadi 61 kata. Persentil ke-95 justru turun dari 202,5 menjadi 129 kata pada Gemma dan dari 213 menjadi 122,5 kata pada Llama, sedangkan acuan berada pada 135 kata. Fine-tuning dengan demikian mengurangi jawaban panjang ekstrem sekaligus membuat panjang respons tipikal lebih mirip target. **[HASIL]**

Keselarasan format tersebut membantu menjelaskan lonjakan F1 dan ROUGE-L. Karena target dan prediksi sama-sama diharapkan menghasilkan pola kutipan–kesimpulan–jawaban, sebagian peningkatan mencerminkan keberhasilan mempelajari format respons, bukan hanya peningkatan pengetahuan faktual. Hal ini bukan kelemahan eksperimen, sebab mengikuti format grounded memang bagian dari tujuan. Namun, klaim yang tepat adalah bahwa fine-tuning meningkatkan **kesesuaian jawaban terhadap evidensi dan target respons pada konteks oracle**, bukan membuktikan akurasi faktual sistem secara mutlak. **[INTERPRETASI]**

Setelah fine-tuning, kedua model mencapai skor yang hampir sama. Gemma sedikit lebih tinggi pada cakupan angka (0,7259 vs 0,7066), Token F1 (0,7236 vs 0,7215), dan IndoBERTScore (0,8911 vs 0,8899), sedangkan Llama sedikit lebih tinggi pada ROUGE-L (0,6525 vs 0,6519). Selisih tersebut sangat kecil dan belum diuji secara statistik antarmodel. Oleh karena itu, evaluasi otomatis belum cukup untuk menetapkan pemenang definitif. Keputusan akhir perlu mempertimbangkan evaluasi manusia, robustnes, dan efisiensi pada perangkat deployment yang sama. **[HASIL dan batas kesimpulan]**

### 4.2.4 Hasil Human Evaluation

#### Rancangan yang telah tersedia

Kode menyiapkan evaluasi buta terhadap tiga dimensi, yaitu *fluency*, *factual correctness*, dan *completeness*, masing-masing pada skala Likert 1–5. Sebesar 1% data uji diambil untuk setiap model dengan seed 42, yaitu 18 pertanyaan per model. Setiap pertanyaan dipasangkan dengan jawaban model dasar dan fine-tuned, sehingga terbentuk 72 item penilaian. Seluruh item diacak, diberi `eval_id` anonim, dan salinan yang sama disiapkan untuk lima evaluator. Evaluator menerima konteks, pertanyaan, jawaban acuan, jawaban model, serta kolom untuk menandai jawaban acuan yang diragukan. **[HASIL dari kode]**

Desain buta dan penggunaan evaluator yang sama untuk seluruh item merupakan kekuatan karena mengurangi pengaruh identitas model dan memungkinkan pengukuran konsistensi antarevaluator. Human evaluation memang dibutuhkan sebagai pelengkap metrik otomatis karena penilaian manusia dapat menilai kewajaran bahasa, kelengkapan, dan ketepatan faktual yang tidak sepenuhnya tercakup oleh kecocokan referensi. Pedoman evaluasi NLG juga menekankan perlunya definisi kriteria, instruksi evaluator, desain unit penilaian, dan pelaporan reliabilitas secara transparan ([van der Lee et al., 2021](https://www.sciencedirect.com/science/article/pii/S088523082030084X)). **[INTERPRETASI dengan dasar literatur]**

#### Bagian hasil yang belum dapat ditulis

Sampai pemeriksaan ini dilakukan, berkas `human_eval_evaluator1.csv` sampai `human_eval_evaluator5.csv` dan `human_eval_key.csv` tidak tersedia pada direktori hasil lokal. Notebook visualisasi juga secara eksplisit melewati seluruh grafik evaluasi manusia. Oleh karena itu, belum ada skor fluency, factual correctness, completeness, uji beda, reliabilitas antarevaluator, maupun proporsi jawaban acuan yang diragukan yang dapat dilaporkan. Setiap angka pada subbagian hasil evaluasi manusia saat ini akan menjadi fabrikasi dan tidak boleh dimasukkan. **[PERLU DILENGKAPI]**

Narasi hasil nantinya dapat mengikuti pola berikut setelah data tersedia:

> Lima evaluator menyelesaikan penilaian terhadap 72 item anonim. Pada Gemma-2, rerata skor fluency/factual correctness/completeness berubah dari [isi] pada kondisi dasar menjadi [isi] setelah fine-tuning. Pada Llama-3.2, skor berubah dari [isi] menjadi [isi]. Perbedaan berpasangan pada tingkat item menunjukkan [isi hasil uji], sedangkan Krippendorff's alpha ordinal sebesar [isi] menunjukkan [interpretasi reliabilitas]. Sebanyak [isi]% penilaian menandai jawaban acuan sebagai meragukan; item tersebut dianalisis terpisah agar kualitas model tidak dinilai menggunakan referensi yang bermasalah. **[TEMPLATE, bukan hasil]**

#### Perbaikan yang diperlukan sebelum evaluasi dijalankan

Pertama, kode mencetak teks “5% sample”, padahal `SAMPLE_FRACTION = 0.01` dan jumlah aktual 18 dari 1.791 atau sekitar 1%. Teks keluaran harus diperbaiki agar tidak menimbulkan inkonsistensi pelaporan. **[HASIL audit kode]**

Kedua, file evaluator hanya memuat kolom skor tanpa rubrik operasional. Rubrik 1–5 harus dibagikan bersama lembar penilaian dan menjelaskan ciri setiap skor pada ketiga kriteria. Tanpa rubrik, perbedaan pemahaman evaluator dapat menurunkan reliabilitas. Sebaiknya dilakukan sesi kalibrasi pada beberapa item latihan yang tidak termasuk sampel analisis. **[PERLU DILENGKAPI; rekomendasi metodologis]**

Ketiga, analisis pada notebook visualisasi menggunakan Mann–Whitney U seolah-olah kondisi base dan fine-tuned merupakan kelompok independen. Padahal evaluator yang sama menilai pertanyaan yang sama pada kedua kondisi, sehingga observasinya berpasangan dan berulang dalam evaluator. Analisis minimal perlu membentuk pasangan berdasarkan evaluator, model, pertanyaan/record, dan kriteria, kemudian menggunakan Wilcoxon signed-rank. Analisis yang lebih kuat dapat menggunakan model ordinal campuran dengan kondisi sebagai efek tetap serta evaluator dan pertanyaan sebagai efek acak. **[HASIL audit statistik; PERLU DILENGKAPI]**

Keempat, Bab III menyatakan bahwa konsistensi antarevaluator diukur dengan Krippendorff's alpha ordinal, tetapi notebook visualisasi belum menghitung alpha. Grafik rerata per evaluator hanya menunjukkan kecenderungan skor dan tidak dapat menggantikan ukuran reliabilitas. Alpha perlu dihitung terpisah untuk setiap kriteria, dan bila relevan juga per model/kondisi, dengan unit yang sama dinilai oleh kelima evaluator. **[PERLU DILENGKAPI]**

Kelima, kolom `ans_ref_meragukan` diinstruksikan diisi “ya”, tetapi kode visualisasi mengubahnya dengan `pd.to_numeric`. Nilai “ya” akan menjadi `NaN`, sehingga persentasenya tidak dapat dihitung. Kolom tersebut harus dinormalisasi secara eksplisit, misalnya `ya=1`, `tidak/kosong=0`, sebelum agregasi. **[HASIL audit kode; PERLU DILENGKAPI]**

Keenam, sampel pertanyaan yang sama kemungkinan terambil untuk kedua model karena kedua berkas prediksi memiliki urutan record yang sama dan menggunakan seed yang sama. Hal ini sebenarnya menguntungkan perbandingan antarmodel, tetapi perlu diverifikasi melalui `record_id` dan dinyatakan eksplisit. Identitas unit pertanyaan juga perlu dipertahankan pada kunci analisis agar uji berpasangan dapat dijalankan. **[INTERPRETASI kode; perlu verifikasi]**

### Sintesis Tujuan 2

Secara keseluruhan, fine-tuning berhasil mengadaptasi kedua SLM terhadap pola QA berbasis konteks publikasi BPS. Bukti terkuatnya adalah penurunan loss validasi yang stabil, peningkatan besar dan konsisten pada Token F1, ROUGE-L, serta IndoBERTScore, peningkatan cakupan angka acuan pada subset numerik, dan kenaikan yang terjadi pada seluruh jenis pertanyaan. Efek terbesar terdapat pada navigasi sumber dan penelusuran fakta, sedangkan perbandingan dan sintesis multi-sumber masih menjadi tugas yang relatif lebih sulit. **[HASIL dan INTERPRETASI]**

Hasil juga memperlihatkan bahwa model berukuran 2–3 miliar parameter dapat diadaptasi secara efisien: kurang dari satu persen parameter dilatih dengan QLoRA, dengan waktu pelatihan sekitar empat sampai enam jam pada lingkungan eksperimen. Setelah fine-tuning, performa Gemma-2 dan Llama-3.2 menjadi hampir sama walaupun Llama-3.2 memperoleh peningkatan relatif lebih besar dari kondisi awal yang lebih rendah. **[HASIL]**

Kesimpulan Tujuan 2 tetap harus dibatasi pada skenario *oracle context*. Dataset tidak memuat *distractor*, hanya 29 dari 47 dokumen terwakili, jawaban acuan dibangkitkan oleh LLM, dan audit manual kualitas dataset belum selesai. Selain itu, evaluasi manusia belum menghasilkan data. Oleh karena itu, rumusan kesimpulan sementara yang aman adalah:

> Fine-tuning QLoRA meningkatkan kemampuan Gemma-2-2B dan Llama-3.2-3B untuk mengikuti format instruksi dan menghasilkan jawaban yang selaras dengan evidensi publikasi BPS ketika konteks relevan telah tersedia. Kedua model mencapai kinerja otomatis yang hampir setara setelah adaptasi. Penetapan model terbaik dan klaim mengenai kualitas faktual akhir masih memerlukan hasil evaluasi manusia serta evaluasi sistem RAG pada kondisi retrieval nyata. **[KESIMPULAN BERBASIS HASIL, dengan pembatasan]**

## Daftar asumsi dan interpretasi yang belum diuji langsung

Bagian berikut sengaja dipisahkan agar tidak dikutip sebagai hasil empiris tanpa pengujian tambahan.

1. **[ASUMSI] Bias kontribusi dokumen.** Konsentrasi 32,57% record pada lima dokumen diduga membuat model lebih akrab dengan topik dan gaya kelima dokumen tersebut. Dugaan ini belum diuji melalui evaluasi *leave-one-document-out* atau perbandingan performa antardokumen.
2. **[ASUMSI] Kompleksitas penalaran.** Delta yang lebih kecil pada `comparative_analysis` dan `multi_source_synthesis` diduga terjadi karena kedua tugas menuntut integrasi beberapa evidensi. Analisis kesalahan manual diperlukan untuk memastikan bahwa penyebabnya benar-benar kompleksitas penalaran, bukan panjang target, komposisi data, atau kualitas referensi.
3. **[ASUMSI] Pembelajaran format.** Kedekatan panjang dan pola jawaban fine-tuned terhadap jawaban acuan menunjukkan bahwa sebagian kenaikan F1 dan ROUGE-L berasal dari keberhasilan meniru format CoT + jawaban. Kontribusi format dan kontribusi kebenaran isi belum dipisahkan melalui ablasi, misalnya mengevaluasi jawaban final saja tanpa CoT.
4. **[ASUMSI] Penyebab percepatan inferensi Gemma.** Durasi inferensi Gemma fine-tuned yang lebih singkat diduga terutama dipengaruhi berkurangnya keluaran panjang ekstrem, bukan karena adaptor membuat komputasi setiap token lebih cepat. Dugaan ini perlu diuji menggunakan token per detik dan jumlah token keluaran aktual.
5. **[ASUMSI] Manfaat CoT pada SLM.** CoT singkat diduga membantu model menghubungkan kutipan dengan jawaban. Penelitian ini belum memiliki kondisi pembanding tanpa CoT, sehingga pengaruh kausal CoT tidak dapat dipisahkan dari pengaruh fine-tuning secara keseluruhan.
6. **[ASUMSI] Dampak sisa data bahasa Inggris.** Empat belas instruksi berbahasa Inggris diduga tidak banyak mengubah hasil agregat karena proporsinya kecil, tetapi dapat memengaruhi analisis kasus dwibahasa dan perlu diverifikasi setelah record tersebut dibersihkan.

## Daftar temuan yang masih kurang atau perlu diperbaiki

1. **Evaluasi manusia belum selesai.** Tidak ada berkas skor evaluator lokal, sehingga subbagian hasil hanya dapat menjelaskan rancangan dan menyediakan template narasi.
2. **Precision-check manual dataset belum diisi.** Notebook hanya menyiapkan 100 sampel record terbuang dan 40 sampel record lolos; kolom keputusan manual masih kosong dan hasil false positive/false negative belum tersedia.
3. **Ada dua notebook evaluasi otomatis yang berbeda.** `tujuan2/evaluation/11-compute-automatic-eval.ipynb` menggunakan cakupan angka dan menghasilkan angka pada `summary_metrics.csv`, sedangkan `tujuan2/[3] evaluation/11-compute-automatic-eval.ipynb` masih memakai kecocokan teks penuh dan menghasilkan EM sekitar 0–0,004. Satu versi otoritatif harus dipilih dan versi lain diarsipkan atau diselaraskan.
4. **Nama metrik EM perlu diperbaiki.** Implementasi aktif adalah *numeric subset accuracy*, bukan Exact Match teks.
5. **Ukuran efek otomatis salah nama.** `proporsi menang − kalah` bukan Cliff's delta standar; gunakan istilah indeks menang–kalah berpasangan atau hitung ukuran efek Wilcoxon yang sesuai.
6. **Uji evaluasi manusia belum sesuai desain.** Mann–Whitney U perlu diganti dengan uji berpasangan atau model ordinal campuran.
7. **Krippendorff's alpha belum diimplementasikan.** Padahal metrik tersebut sudah dijanjikan pada Bab III.
8. **Parsing `ans_ref_meragukan` belum benar.** Kode numerik tidak dapat membaca jawaban teks “ya”.
9. **Teks persentase sampel manusia salah.** Kode memakai 1%, tetapi keluaran mencetak 5%.
10. **Dataset final masih memuat sedikit instruksi bahasa Inggris.** Sedikitnya 14 instruksi terdeteksi dengan pola pembuka bahasa Inggris dan perlu ditinjau.
11. **Skor kualitas 0,9518 bukan skor dataset final.** Nilai itu dihitung sebelum hard gate; rerata `track_a_score` pada berkas final adalah 0,9682.
12. **PNG hasil visualisasi belum tersimpan di repositori.** Notebook memuat grafik sebagai output, tetapi folder `Visualisasi` belum berisi berkas `fig*.png` untuk Tujuan 2.
13. **Perbandingan waktu lintas model tidak setara.** Gemma menggunakan dua GPU pada inferensi, sedangkan Llama menggunakan satu GPU.
14. **Evaluasi safetensors dan GGUF belum sama-sama tersedia pada Tujuan 2.** Bab III menyebut dua format evaluasi, tetapi hasil lokal Tujuan 2 yang tersedia baru merepresentasikan prediksi model 4-bit/adapter dalam notebook generasi saat ini.

## Rekomendasi urutan tabel dan gambar di Bab IV

1. Funnel korpus ke dataset final: 47 dokumen → 29 dokumen terwakili → 12.261 record mentah → 9.350 record akhir.
2. Distribusi sembilan sub-tugas dan kontribusi dokumen.
3. Tabel konfigurasi QLoRA kedua model.
4. Kurva training loss dan validation loss.
5. Tabel skor otomatis base versus fine-tuned.
6. Grafik delta per metrik dan per sub-tugas.
7. Satu atau dua contoh jawaban sebelum–sesudah fine-tuning, termasuk satu contoh berhasil dan satu contoh regresi.
8. Setelah tersedia: tabel skor human evaluation, distribusi Likert, dan Krippendorff's alpha ordinal.
