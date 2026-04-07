from Detection.preprocessing import preprocess_image
from Detection.model_loader import load_model
from Detection.predictor import predict
from Detection.anomaly import evaluate_anomaly
from Detection.adversarial import is_adversarial

model = load_model()

def process_image(image_file):

    # Step 1: preprocess
    input_tensor = preprocess_image(image_file)

    # Step 2: prediction
    result = predict(model, input_tensor)

    confidence = result["confidence"]
    probs = result["probs"]
    top5 = result["top5"]

    # Step 3: anomaly detection
    anomaly_result = evaluate_anomaly(probs)

    # Step 4: adversarial detection
    adv_result = is_adversarial(model, input_tensor)

    issues = []
    issues.extend(anomaly_result["reasons"])
    issues.extend(adv_result["reasons"])

    transform_unstable = bool(adv_result["transform"]["unstable_transforms"])

    if anomaly_result["flag"] and adv_result["flag"]:
        verdict = "suspicious"
    elif transform_unstable:
        verdict = "suspicious"
    elif anomaly_result["flag"] or adv_result["flag"]:
        verdict = "uncertain"
    else:
        verdict = "reliable"

    return {
        "prediction": result["class"],
        "label": result["label"],
        "confidence": confidence,
        "top5": top5,
        "anomaly": anomaly_result["flag"],
        "adversarial": adv_result["flag"],
        "verdict": verdict,
        "anomaly_score": anomaly_result["score"],
        "top1_confidence": anomaly_result["top1_confidence"],
        "top2_confidence": anomaly_result["top2_confidence"],
        "margin": anomaly_result["margin"],
        "entropy": anomaly_result["entropy"],
        "normalized_entropy": anomaly_result["normalized_entropy"],
        "fgsm_confidence_drop": adv_result["fgsm"]["confidence_drop"],
        "transform_confidence_drop": adv_result["transform"]["largest_conf_drop"],
        "transform_instability": adv_result["transform"]["unstable_transforms"],
        "issues": issues,
    }
