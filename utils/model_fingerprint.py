import hashlib


def sha256_for_model(model):
    digest = hashlib.sha256()

    for name in sorted(model.state_dict().keys()):
        tensor = model.state_dict()[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tensor.dtype).encode("utf-8"))
        digest.update(str(tuple(tensor.shape)).encode("utf-8"))
        digest.update(tensor.numpy().tobytes())

    return digest.hexdigest()
