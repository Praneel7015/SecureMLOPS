import { Upload, Image as ImageIcon } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { useRef, useState } from 'react';

interface InputPageProps {
  samples: any[];
}

export function InputPage({ samples }: InputPageProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedSample, setSelectedSample] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setSelectedSample('');
    }
  };

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <Card>
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold mb-2">Analysis Input</h2>
            <p className="font-mono text-sm text-muted-foreground mb-4">Use this page to upload or choose a sample image</p>

            <div className="space-y-4">
              <Label>Upload Image</Label>
              <Card className="border-dashed cursor-pointer hover:border-accent transition-colors bg-muted/30" onClick={() => fileInputRef.current?.click()}>
                <CardContent className="p-6 flex flex-col items-center text-center">
                  {selectedFile ? (
                    <div className="relative w-full">
                      <img src={URL.createObjectURL(selectedFile)} alt="Preview" className="mx-auto max-h-48 object-contain rounded-md" />
                      <p className="mt-4 font-mono text-sm truncate">{selectedFile.name}</p>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground mb-1">Click or drag & drop</p>
                      <p className="font-mono text-xs text-muted-foreground">.jpg, .jpeg, .png</p>
                    </>
                  )}
                </CardContent>
              </Card>
              <input ref={fileInputRef} type="file" onChange={handleFileChange} className="hidden" />

              <div>
                <Label>Or Select Sample</Label>
                <div className="grid gap-2">
                  {samples.map((sample) => (
                    <label key={sample.value} className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-muted transition-colors">
                      <input type="radio" name="sample" value={sample.value} onChange={() => setSelectedSample(sample.value)} className="hidden" />
                      {sample.url ? <img src={sample.url} alt={sample.label} className="w-8 h-8 rounded object-cover" /> : <ImageIcon className="w-4 h-4 text-muted-foreground" />}
                      <span className="flex-1 font-mono text-sm">{sample.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <Button className="w-full">Run Analysis</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
