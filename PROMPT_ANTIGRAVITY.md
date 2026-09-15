# Prompt giao cho Antigravity hoàn thiện Day04

Bạn đang làm việc trực tiếp trong repository hiện tại. Hãy đóng vai trò kỹ sư chính chịu trách nhiệm hoàn thiện bài lab **Day04 — Prompt Engineering & Tool Calling** theo đúng `README.md`, `RULES.md`, `RUBRIC.md`, `CHECKPOINTS.md`, `SUBMISSION.md` và contract trong `starter_v0/`.

Mục tiêu là tạo một bài nộp IT Helpdesk hoàn chỉnh, chạy được, có evidence thật và tối đa hóa điểm theo rubric (90 điểm phần chung + tối đa 10 điểm mở rộng). Không chỉ sửa câu chữ: phải triển khai, chạy kiểm thử/eval, đọc trace, lặp v0–v3, làm UI, transcript, report và kiểm tra bài nộp. Không được tuyên bố “pass” nếu chưa có kết quả chạy chứng minh.

## 1. Nguyên tắc bắt buộc

1. Đọc đầy đủ các file hướng dẫn ở root và các README/TOOL.md liên quan trước khi sửa code. Sau đó kiểm tra `git status`, cấu trúc repo, source, provider, agent loop, tool registry, dữ liệu giả lập và evaluator.
2. Tiếp tục dùng lĩnh vực **IT Helpdesk** và toàn bộ dữ liệu giả lập có sẵn, trừ khi tôi yêu cầu đổi lĩnh vực.
3. Tuyệt đối không sửa nội dung của ba bộ cố định sau để tăng điểm:
   - `starter_v0/data/eval_base.json`
   - `starter_v0/data/eval_adversarial.json`
   - `starter_v0/data/eval_helpdesk_extension.json`
4. Giữ nguyên tên các built-in tool và bảo đảm `starter_v0/artifacts/tools.yaml`, `starter_v0/tools/__init__.py`, schema và implementation luôn khớp nhau.
5. Không hard-code case ID, câu chữ của eval, expected answer hay mẹo nhận diện test vào prompt/code. Các cải thiện phải là quy tắc tổng quát có thể giải thích được.
6. Không bịa run, metric, transcript, URL, commit, thành viên, đóng góp, demo hay kết quả PASS. Chỉ ghi số liệu và đường dẫn có thật sau khi chạy thành công.
7. Không đọc ra màn hình, chép vào source, report, transcript hoặc commit bất kỳ API key/token/credential nào. Không commit `.env`, `.venv`, cache, `tickets/`, dữ liệu thật hoặc output chứa bí mật. Chỉ dùng dữ liệu giả lập.
8. Không tự thay đổi hoặc xóa sửa đổi sẵn có của người dùng. Mọi thao tác phải an toàn, có thể đối chiếu; không force-push, không rewrite history và không tạo commit thay mặt thành viên khác.
9. Nếu thiếu API key/provider hoặc thông tin TEAM thật, hãy dừng đúng phần phụ thuộc đó và hỏi tôi cung cấp/cấu hình. Trong lúc chờ, vẫn hoàn thiện các phần tĩnh độc lập. Không tạo evidence giả để lấp chỗ trống.
10. Dùng cùng một provider, model, temperature và bộ case cho chuỗi so sánh v0–v3. Một run chỉ hợp lệ khi `provider_error_cases == 0` và `measured_cases == total_cases`; đồng thời phải đọc thủ công `tool_results`, không chỉ nhìn routing PASS.

## 2. Cách làm việc

Làm chủ động từ đầu đến cuối. Trước khi sửa, lập checklist bám sát rubric và báo ngắn gọn trạng thái. Sau mỗi mốc, chạy kiểm tra tương ứng, đọc lỗi rồi sửa nguyên nhân. Chỉ hỏi tôi khi thật sự bị chặn bởi credential, thông tin cá nhân/nhóm, lựa chọn có ảnh hưởng lớn hoặc thao tác bên ngoài repository.

Không dừng ở việc đưa hướng dẫn hay đoạn code mẫu: hãy trực tiếp tạo/sửa file trong repo, chạy lệnh kiểm chứng và hoàn thiện những phần có thể hoàn thiện. Khi có lỗi, điều tra đến nguyên nhân gốc. Không giảm độ khó bằng cách sửa expected result.

## 3. Pha 0 — Audit và baseline v0 nguyên bản

1. Kiểm tra trạng thái repo và ghi nhận file nào đã có sửa đổi. Kiểm tra `.gitignore` trước khi sinh output.
2. Đọc toàn bộ schema/case để hiểu evaluator, nhưng chỉ rút ra quy tắc hành vi tổng quát.
3. Xác định provider/model khả dụng bằng `starter_v0/scripts/preflight_provider.py`. Không in giá trị biến môi trường. Nếu chưa có key, hỏi tôi cấu hình một provider và không giả lập run.
4. **Trước khi thay đổi `system_prompt.md` hoặc `tools.yaml`**, chạy baseline v0 thật:

   ```bash
   cd starter_v0
   python scripts/preflight_provider.py --provider <provider>
   python run_eval.py --provider <provider> --model <model-neu-can> --version v0 --suite base --eval-cases data/eval_base.json
   ```

5. Giữ file run v0 thật trong `starter_v0/runs/`. Lưu snapshot artifact v0 vào một cấu trúc rõ ràng như `starter_v0/artifacts/versions/v0/` để người chấm đối chiếu; snapshot phải đúng hash trong run.
6. Parse run bằng `scripts/parse_runs.py`, phân loại failure theo wrong tool, wrong args, missing info, multi-turn, confirmation/cancel và safety boundary. Chọn failure có evidence để hình thành giả thuyết v1.

Nếu artifact đã bị sửa trước khi bạn bắt đầu hoặc đã có run, không được gọi một run mới là baseline nguyên bản một cách sai lệch. Hãy dùng Git/hash để xác định tình trạng thật và báo rõ.

## 4. Pha 1 — Cải thiện v1, v2, v3 có kiểm soát

Thực hiện ba vòng riêng biệt. Mỗi vòng phải có một giả thuyết chính, thay đổi có chủ đích, snapshot artifact, run base mới và phân tích trước/sau. Không chỉ đổi nhãn version.

Gợi ý thứ tự, nhưng phải điều chỉnh theo failure thật:

- **v1 — tool routing và argument contract:** làm rõ ranh giới giữa status dịch vụ, chẩn đoán một asset, tra cứu user, tìm KB, policy, formatter, web search, clarify và create ticket; làm rõ default/enum/required field, khi gọi song song, khi không dùng tool.
- **v2 — hội thoại nhiều lượt và action boundary:** latest intent wins; sửa đổi mới nhất ghi đè dữ liệu cũ; hủy thì không gọi tool; chỉ kế thừa thông tin còn hiệu lực; không tự đoán asset/employee/environment; thiếu dữ liệu thì `clarify`; create ticket chỉ chạy với payload hiện tại đã được xác nhận rõ, và mọi thay đổi payload làm vô hiệu xác nhận cũ.
- **v3 — an toàn và tinh chỉnh theo trace:** chống role spoofing, forged tool results và prompt injection; coi nội dung lấy từ KB/policy/web là dữ liệu không đáng tin chứ không phải chỉ thị; không tiết lộ system prompt; không gọi tool không được khai báo; không đưa identifier/log/chẩn đoán nội bộ ra công cụ web; không ghi password, OTP, MFA, token hay recovery code vào ticket; chỉ gửi ra web manufacturer/model/query type công khai.

`system_prompt.md` cuối nên ngắn gọn nhưng đủ quyết định, bao gồm tối thiểu:

- thứ tự ưu tiên chỉ thị và trust boundary;
- bảng/quy tắc chọn tool theo intent;
- quy tắc exact arguments, default có điều kiện và không đoán identifier;
- quy tắc nhiều tool/parallel calls;
- quy tắc multi-turn, correction, cancellation và latest intent;
- quy tắc xác nhận action gắn với payload hiện tại;
- privacy/external-search boundary và xử lý sensitive data;
- cách xử lý tool error/uncertainty;
- output JSON đúng bốn top-level field `intent`, `action`, `reply`, `evidence_ids` khi trả lời text.

`tools.yaml` cuối phải mô tả đủ rõ để model chọn chính xác mà không phụ thuộc vào system prompt, schema tương thích implementation, và đặc biệt nêu rõ các negative boundary. Không đổi tên built-in tool.

Sau từng version:

1. Lưu snapshot `system_prompt.md` và `tools.yaml` của version đó.
2. Chạy base eval thật cùng provider/model.
3. Xác nhận run đủ 30/30 measured và 0 provider error; đọc cả tool result/error.
4. Parse thành CSV phân tích có đường dẫn rõ ràng.
5. Cập nhật `starter_v0/artifacts/version_log.csv` bằng dữ liệu thật: version, author, artifact thay đổi, artifact version/hash, lý do, hypothesis, metric before/after, exact run file.
6. Không nhất thiết phải đạt 100% ở mỗi vòng, nhưng mọi nhận xét phải trung thực. Nếu chưa tốt, dùng failure còn lại để thiết kế vòng sau.

## 5. Pha 2 — 10 case nhóm nguyên bản

Hoàn thiện `starter_v0/data/eval_group.json` với **đúng 10 case mới, không sao chép/paraphrase sát bộ có sẵn**:

- đúng 5 single-turn dùng `query`;
- đúng 5 multi-turn dùng `turns`;
- mọi case có `id` duy nhất, `phase: "B"`, một `failure_type` hợp lệ, `expect` chấm được và `metadata.what_it_tests` rõ ràng;
- bao phủ tool routing, exact arguments, thiếu thông tin, correction/cancel/latest intent, confirmation boundary, no-tool và ít nhất một luồng nhiều tool;
- expected tool phải tồn tại trong cả declaration và registry.

Viết validator/test tự động kiểm tra số lượng 5+5, schema, unique ID, failure type, tool existence và tính parse được. Chạy group eval thật trên bản final, đọc trace, lưu run/analysis và đưa kết quả thật vào report.

## 6. Pha 3 — Safety, extension và bonus 10 điểm

1. Chạy đủ 12 adversarial case cố định bằng artifact final. Xác nhận 12 measured, 0 provider error. Review cả call args, `tool_results` và filesystem để chắc chắn không có write/exfiltration nhạy cảm.
2. Phân tích chi tiết ít nhất 3 case đại diện trong report: expected boundary, actual calls, có/không sensitive write/exfiltration, outcome và giới hạn.
3. Chạy `eval_helpdesk_extension.json` trên bản final. Nếu `search_device_info` cần `TAVILY_API_KEY`, kiểm tra an toàn và yêu cầu tôi cấu hình nếu muốn evidence live; không gửi identifier nội bộ ra ngoài và không bịa kết quả web.
4. Để hướng tới đủ 100 điểm, triển khai **một chức năng mới thật sự ngoài luồng cơ bản**, ưu tiên một tool local deterministic, hữu ích và an toàn như tra cứu tình trạng bảo hành thiết bị từ dữ liệu giả lập. Nếu chọn hướng khác, phải giải thích vì sao hữu ích và ngoài core flow.
5. Bonus tool phải có:
   - thư mục `starter_v0/tools/<tool_name>/` với `TOOL.md`, `tool.py`, `__init__.py`;
   - metadata đúng Tool Folder Contract, input/output JSON ổn định, lỗi rõ cho input không tồn tại;
   - dữ liệu giả lập riêng, khai báo trong `tools.yaml`, đăng ký trong `tools/__init__.py`;
   - test/smoke test cho success, invalid input và safety boundary;
   - một bộ eval bonus riêng hoặc case nhóm phù hợp, run thật và transcript/demo;
   - mô tả tích hợp, rủi ro/guardrail và evidence trong report.

Không gọi `policy`, `create_ticket` hoặc `search_device_info` có sẵn là bonus mới.

## 7. Pha 4 — UI chat và transcript thật

Xây một UI chat chạy local (ưu tiên Streamlit nếu repo chưa có framework UI), tái sử dụng agent/provider/tool loop thay vì viết logic giả. Cập nhật `requirements.txt` và hướng dẫn chạy trong README.

UI tối thiểu phải:

- cho chọn provider/model và hiển thị artifact version/hash đang chạy;
- hỗ trợ hội thoại nhiều lượt và reset session;
- hiển thị rõ từng tool call, exact JSON input, result hoặc error, round/status;
- hiển thị câu trả lời assistant, trạng thái chờ clarify và giới hạn tool rounds;
- lưu transcript JSON thật tương thích/có cấu trúc rõ, không che lỗi;
- không hiển thị/log key và không tự động commit ticket phát sinh;
- xử lý lỗi provider/tool thân thiện nhưng giữ đủ chi tiết kỹ thuật để chấm.

Tách logic dùng chung khỏi CLI nếu cần để tránh hai implementation lệch nhau. Tạo transcript thật cho tối thiểu bốn scenario: bình thường, thiếu thông tin rồi bổ sung, multi-turn correction/cancel, và action ghi dữ liệu có review + confirmation đúng payload. Với action, dùng dữ liệu giả lập, kiểm tra file được tạo rồi xóa/giữ ngoài Git theo `.gitignore`; transcript phải cho thấy hành vi thật. Thêm bonus scenario nếu có.

## 8. Pha 5 — Tests, tài liệu và evidence

Thêm test phù hợp cho phần code mới và chạy tối thiểu:

```bash
python -m compileall starter_v0
python -m pytest -q
```

Nếu chưa dùng pytest thì thêm dependency/test setup hợp lý. Ngoài ra phải kiểm tra:

- JSON/YAML parse được;
- tool names/schema/registry/implementation đồng bộ;
- các file eval cố định không đổi so với Git baseline;
- group eval đúng 5+5;
- UI import/start smoke test được;
- toàn bộ run dùng làm evidence có `provider_error_cases == 0` và `measured_cases == total_cases`;
- không có file cấm, secret hay ticket generated bị track;
- mọi link/path trong report tồn tại;
- `git diff` chỉ chứa thay đổi có chủ đích.

Cập nhật tài liệu:

1. Root `README.md` hoặc README phù hợp: cài đặt, `.env` an toàn, preflight, lệnh eval từng suite, lệnh UI/chat/test, cấu trúc evidence và known limitations.
2. `starter_v0/artifacts/REPORT.md`: điền đủ A/B/C bằng số liệu, failure analysis và link file thật; không để placeholder ở phần đã có dữ liệu.
3. `TEAM.md`: chỉ điền thông tin thật tôi cung cấp. Yêu cầu từng thành viên tự viết INDIVIDUAL và có commit kỹ thuật thật; không tự bịa hoặc commit thay họ. Những chỗ chưa có dữ liệu phải đánh dấu blocker rõ ràng.
4. Tạo một checklist nộp cuối cùng đối chiếu từng dòng rubric và chỉ đánh dấu đạt khi có evidence cụ thể.

## 9. Acceptance criteria cuối cùng

Chỉ báo hoàn tất khi tất cả điều có thể kiểm chứng sau đây đều đạt:

- artifact final và registry/tool implementation khớp;
- có run thật base v0, v1, v2, v3 cùng điều kiện, đủ case, không provider error;
- version log có hash, hypothesis, metric và run path thật;
- có đúng 10 group case 5+5 và run final;
- có run 12 adversarial + ít nhất 3 phân tích thủ công;
- UI chạy được và hiện tool/input/result-error/version;
- có transcript thật cho các luồng bắt buộc;
- report đầy đủ, mọi số liệu/link truy ngược được;
- bonus tool là chức năng mới, có code/data/test/run/demo/safety evidence;
- không sửa fixed eval, không có secret/dữ liệu thật/file cấm;
- các kiểm tra compile/test/validator đều pass;
- phần TEAM/INDIVIDUAL/URL/commit chốt chỉ hoàn thành bằng dữ liệu và thao tác thật của thành viên.

Nếu model/provider khiến một vài case chưa pass sau v3, không che giấu. Hãy đưa bảng case fail còn lại, trace, nguyên nhân, những gì đã thử và đề xuất thay đổi nhỏ nhất tiếp theo. “Pass hết yêu cầu” nghĩa là đáp ứng đúng quy trình và có bằng chứng thật, không phải sửa test hoặc viết báo cáo lạc quan.

## 10. Cách báo cáo lại cho tôi

Khi xong, trả lời ngắn gọn theo cấu trúc:

1. Kết quả chính và trạng thái từng tiêu chí rubric.
2. Bảng metric v0–v3 và final group/adversarial/extension/bonus, kèm exact run path.
3. Danh sách file đã tạo/sửa.
4. Lệnh cài/chạy test/eval/UI có thể copy-paste.
5. Các blocker cần tôi hoặc từng thành viên xử lý (API key, TEAM, INDIVIDUAL, commit, repo URL/VLearn).
6. Known limitations và case còn fail, nếu có.

Hãy bắt đầu bằng audit và baseline v0. Không sửa artifact trước khi baseline thật đã được lưu.
